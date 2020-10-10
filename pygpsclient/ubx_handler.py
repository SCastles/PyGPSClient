'''
UBX Protocol handler

Uses pyubx2 library for parsing

Created on 30 Sep 2020

@author: semuadmin
'''
# pylint: disable=invalid-name

from pyubx2 import UBXMessage, POLL, UBX_CONFIG_MESSAGES


CFG_MSG_OFF = b'\x00\x00\x00\x00\x00\x01'
CFG_MSG_ON = b'\x00\x01\x01\x01\x00\x01'
BOTH = 3
UBX = 1
NMEA = 2


class UBXHandler():
    '''
    UBXHandler class
    '''

    def __init__(self, app):
        '''
        Constructor.
        '''

        self.__app = app  # Reference to main application class
        self.__master = self.__app.get_master()  # Reference to root class (Tk)

        self._raw_data = None
        self._parsed_data = None
        self.gsv_data = []  # Holds array of current satellites in view from NMEA GSV sentences
        self.lon = 0
        self.lat = 0
        self.alt = 0
        self.track = 0
        self.speed = 0
        self.pdop = 0
        self.hdop = 0
        self.vdop = 0
        self.hacc = 0
        self.vacc = 0
        self.utc = ''
        self.sip = 0
        self.fix = '-'
        self.ubx_state = {} # dict containing current UBX device config

    @staticmethod
    def poll_ubx_config(serial):
        '''
        POLL current UBX device configuration (port protocols
        and message rates).

        NB: The responses and acknowledgements to these polls
        may take several seconds to arrive and will only be
        processed if the input protocol is set to UBX or BOTH
        '''
        # TODO block access to UBX-Config if in NMEA only mode?

        for msgtype in ('CFG-PRT', 'CFG-USB'):
            msg = UBXMessage('CFG', msgtype, None, POLL)
            serial.write(msg.serialize())

        for payload in UBX_CONFIG_MESSAGES:
            msg = UBXMessage('CFG', 'CFG-MSG', payload, POLL)
            serial.write(msg.serialize())

        msg = UBXMessage('CFG', 'CFG-INF', b'\x00', POLL)
        serial.write(msg.serialize())

    def process_data(self, data: bytes) -> UBXMessage:
        '''
        Process UBX message type
        '''

        parsed_data = UBXMessage.parse(data, False)

        if parsed_data.identity == 'CFG-MSG':
            self._process_CFG_MSG(parsed_data)
        if parsed_data.identity == 'CFG-PRT':
            self._process_CFG_PRT(parsed_data)
        if parsed_data.identity == 'CFG-INF':
            self._process_CFG_INF(parsed_data)
        if parsed_data.identity == 'NAV-POSLLH':
            self._process_NAV_POSLLH(parsed_data)
        if parsed_data.identity == 'NAV-PVT':
            self._process_NAV_PVT(parsed_data)
        if parsed_data.identity == 'NAV-VELNED':
            self._process_NAV_VELNED(parsed_data)
        if parsed_data.identity == 'NAV-SVINFO':
            self._process_NAV_SVINFO(parsed_data)
        if parsed_data.identity == 'NAV-SOL':
            self._process_NAV_SOL(parsed_data)
        if parsed_data.identity == 'NAV-DOP':
            self._process_NAV_DOP(parsed_data)
        if data or parsed_data:
            self._update_console(data, parsed_data)

        return parsed_data

    def _update_console(self, raw_data, parsed_data):
        '''
        Write the incoming data to the console in raw or parsed format.
        '''

        if self.__app.frm_settings.get_settings()['raw']:
            self.__app.frm_console.update_console(str(raw_data))
        else:
            self.__app.frm_console.update_console(str(parsed_data))

    def _process_CFG_MSG(self, data: UBXMessage):
        '''
        Process CFG-MSG sentence - UBX message configuration.
        Update the UBX state dictionary to reflect current UBX device config.
        '''

        msgtype = UBX_CONFIG_MESSAGES[data.msgClass + data.msgID]
        rates = (data.rateDDC, data.rateUART1, data.rateUART2, data.rateUSB,
                 data.rateSPI, data.reserved)
        self.ubx_state[msgtype] = rates

    def _process_CFG_INF(self, data: UBXMessage):
        '''
        Process CFG-INF sentence - UBX info message configuration.
        Update the UBX state dictionary to reflect current UBX device config.
        '''

        cfg = (data.infMsgMaskDDC, data.infMsgMaskUART1, data.infMsgMaskUART2,
               data.infMsgMaskUSB, data.infMsgMaskSPI)
        self.ubx_state['CFG-INF'] = cfg

    def _process_CFG_PRT(self, data: UBXMessage):
        '''
        Process CFG-PRT sentence - UBX port configuration.
        Update the UBX state dictionary to reflect current UBX device config.
        '''

        cfg = (data.mode, data.baudRate, data.inProtoMask, data.outProtoMask)
        self.ubx_state['CFG-PRT'] = cfg

    def _process_NAV_POSLLH(self, data: UBXMessage):
        '''
        Process NAV-LLH sentence - Latitude, Longitude, Height.
        '''

        try:
            self.utc = UBXMessage.itow2utc(data.iTOW)
            self.lat = data.lat / 10 ** 7
            self.lon = data.lon / 10 ** 7
            self.alt = data.hMSL / 1000
            self.hacc = data.hAcc / 1000
            self.vacc = data.vAcc / 1000
            self.__app.frm_banner.update_banner(time=self.utc, lat=self.lat,
                                                lon=self.lon, alt=self.alt,
                                                hacc=self.hacc, vacc=self.vacc)

            if self.__app.frm_settings.get_settings()['webmap']:
                self.__app.frm_mapview.update_map(self.lat, self.lon, self.hacc,
                                                  self.vacc, '3D', False)
            else:
                self.__app.frm_mapview.update_map(self.lat, self.lon, self.hacc,
                                                  self.vacc, '3D', True)
        except ValueError:
            # self.__app.set_status(ube.UBXMessageError(err), "red")
            pass

    def _process_NAV_PVT(self, data: UBXMessage):
        '''
        Process NAV-PVT sentence -  Navigation position velocity time solution
        '''

        try:
            self.utc = UBXMessage.itow2utc(data.iTOW)
            self.lat = data.lat / 10 ** 7
            self.lon = data.lon / 10 ** 7
            self.alt = data.hMSL / 1000
            self.hacc = data.hAcc / 1000
            self.vacc = data.vAcc / 1000
            self.pdop = data.pDOP
            self.sip = data.numSV
            self.speed = data.gSpeed / 100
            self.track = data.headMot / 10 ** 5
            fix = UBXMessage.gpsfix2str(data.fixType)
            self.__app.frm_banner.update_banner(time=self.utc, lat=self.lat,
                                                lon=self.lon, alt=self.alt,
                                                hacc=self.hacc, vacc=self.vacc,
                                                pdop=self.pdop, sip=self.sip,
                                                speed=self.speed, fix=fix,
                                                track=self.track)

            if self.__app.frm_settings.get_settings()['webmap']:
                self.__app.frm_mapview.update_map(self.lat, self.lon, self.hacc,
                                                  self.vacc, '3D', False)
            else:
                self.__app.frm_mapview.update_map(self.lat, self.lon, self.hacc,
                                                  self.vacc, '3D', True)
        except ValueError:
            # self.__app.set_status(ube.UBXMessageError(err), "red")
            pass

    def _process_NAV_VELNED(self, data: UBXMessage):
        '''
        Process NAV-VELNED sentence - Velocity Solution in North East Down format.
        '''

        try:
            self.track = data.heading / 10 ** 5
            self.speed = data.gSpeed / 100
            self.__app.frm_banner.update_banner(speed=self.speed, track=self.track)
        except ValueError:
            # self.__app.set_status(ube.UBXMessageError(err), "red")
            pass

    def _process_NAV_SVINFO(self, data: UBXMessage):
        '''
        Process NAV-SVINFO sentences - Space Vehicle Information.
        '''

        try:
            self.gsv_data = []
            num_siv = int(data.numCh)
            self.__app.frm_banner.update_banner(siv=num_siv)

            for i in range(num_siv):
                idx = "_{0:0=2d}".format(i + 1)
                # TODO is there an easier/better way to do this without exec()?:
                exec("self.gsv_data.append((data.svid" + str(idx) + \
                     ", data.elev" + str(idx) + \
                     ", data.azim" + str(idx) + ", data.cno" + str(idx) + "))")
            self.__app.frm_satview.update_sats(self.gsv_data)
            self.__app.frm_graphview.update_graph(self.gsv_data, num_siv)
        except ValueError:
            # self.__app.set_status(ube.UBXMessageError(err), "red")
            pass

    def _process_NAV_SOL(self, data: UBXMessage):
        '''
        Process NAV-SOL sentence - Navigation Solution.
        '''

        try:
            self.pdop = data.pDOP / 100
            self.sip = data.numSV
            fix = UBXMessage.gpsfix2str(data.gpsFix)

            self.__app.frm_banner.update_banner(dop=self.pdop, fix=fix, sip=self.sip)
        except ValueError:
            # self.__app.set_status(ube.UBXMessageError(err), "red")
            pass

    def _process_NAV_DOP(self, data: UBXMessage):
        '''
        Process NAV-DOP sentence - Dilution of Precision.
        '''

        try:
            self.pdop = data.pDOP / 100
            self.hdop = data.hDOP / 100
            self.vdop = data.vDOP / 100

            self.__app.frm_banner.update_banner(dop=self.pdop, hdop=self.hdop, vdop=self.vdop)
        except ValueError:
            # self.__app.set_status(ube.UBXMessageError(err), "red")
            pass

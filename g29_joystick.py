# https://blog.thea.codes/talking-to-gamepads-without-pygame/ <-- winner winner chicken dinner
import hid  # python module: "hidapi"
import struct
import time


from enum import Enum

end_joy = False         # global variable to close joystick polling


class G29_JOY_INPUT_ENUM(Enum):
    AXIS_WHEEL = 0
    AXIS_PEDAL_RHT = 1
    AXIS_PEDAL_MID = 2
    AXIS_PEDAL_LFT = 3

    # Change in Byte[5][3:0]
    BTN_DPAD_UP  = 4  # enumeration
    BTN_DPAD_RHT = 5  #
    BTN_DPAD_DWN = 6
    BTN_DPAD_LFT = 7

    # Change in Byte[5][7:4]
    BTN_SQUARE = 8    # bit 4
    BTN_X = 9         # bit 5
    BTN_CIRCLE = 10   # bit 6
    BTN_TRIANGLE = 11 # bit 7

    # Change in Byte[6]
    BTN_L1 = 12       # bit 0
    BTN_R1 = 13       # bit 1
    BTN_L2 = 14       # bit 2
    BTN_R2 = 15       # bit 3
    BTN_SHARE = 16    # bit 4
    BTN_OPTION = 17   # bit 5
    BTN_L3 = 18       # bit 6
    BTN_R3 = 19       # bit 7

    # Change in Byte[7]
    BTN_SONY = 20     # bit 0

    # Change in Byte 54
    BTN_ENTER = 21    # bit 0
    BTN_ROT_CCW = 22  # bit 1
    BTN_ROT_CW = 23   # bit 2
    BTN_MINUS = 24    # bit 3
    BTN_PLUS = 25     # bit 4


class g29_joystick:
    global end_joy
    isPrint = False

    G29_VID = 0x046D
    G29_PID_PS3 = 0xC294    # <----- DONT USE THIS MODE
    G29_PID_PS4 = 0xC260

    dpad_lut_callback_indices = {
        0: [G29_JOY_INPUT_ENUM.BTN_DPAD_UP],
        1: [G29_JOY_INPUT_ENUM.BTN_DPAD_UP, G29_JOY_INPUT_ENUM.BTN_DPAD_RHT],
        2: [G29_JOY_INPUT_ENUM.BTN_DPAD_RHT],
        3: [G29_JOY_INPUT_ENUM.BTN_DPAD_RHT, G29_JOY_INPUT_ENUM.BTN_DPAD_DWN],
        4: [G29_JOY_INPUT_ENUM.BTN_DPAD_DWN],
        5: [G29_JOY_INPUT_ENUM.BTN_DPAD_DWN, G29_JOY_INPUT_ENUM.BTN_DPAD_LFT],
        6: [G29_JOY_INPUT_ENUM.BTN_DPAD_LFT],
        7: [G29_JOY_INPUT_ENUM.BTN_DPAD_LFT, G29_JOY_INPUT_ENUM.BTN_DPAD_UP],
        8: []
    }

    def __init__(self, isPrint=False):
        g29_joystick.isPrint = isPrint

        self.check_for_device()
        self.gamepad = hid.device()
        self.gamepad.open(self.G29_VID, self.G29_PID_PS4)
        self.gamepad.set_nonblocking(False)     # rely on callbacks to be called every report delta.

        self.internal_callback_lut = {
            5: self.parse_byte5, 6: self.parse_byte6, 7: self.parse_byte7,
            43: self.parse_axis_wheel, 44: self.parse_axis_wheel,
            45: self.parse_axis_pedal_rht, 46: self.parse_axis_pedal_rht,
            47: self.parse_axis_pedal_mid, 48: self.parse_axis_pedal_mid,
            49: self.parse_axis_pedal_lft, 50: self.parse_axis_pedal_lft,
            54: self.parse_byte54
        }

        self.ext_callbacks = {enum_val: g29_joystick.default_callback for enum_val in G29_JOY_INPUT_ENUM}
        self.buff_prev = None

    def check_for_device(self):
        devices = hid.enumerate()

        if self.G29_VID not in [dev['vendor_id'] for dev in devices]:
            raise Exception('Logitech G29 NOT CONNECTED.')

        if self.G29_PID_PS4 not in [dev['product_id'] for dev in devices]:
            raise Exception('Logitech G29 NOT SET TO PS4 MODE!')

    # TOOD: Rename to on change callback.
    def set_callback(self, input_code, callback_func):
        if input_code in self.ext_callbacks:
            self.ext_callbacks[input_code] = callback_func

    # TODO: Add callbacks on update.
    # TODO: Add callbacks on button press.

    def run(self):
        buff_prev = None

        # queue up all callbacks to initial values.
        # TODO!

        # Run task of reading
        while not end_joy:
            buff = self.gamepad.read(max_length=64)    # why 64? meh


            print(' '.join([f'{i:X}:{x:02X}' for i, x in enumerate(buff)]))

            # if buff_prev is None:
            #     print(' '.join([f'{i:X}:{x:02X}' for i, x in enumerate(buff)]))
            if buff_prev:
                buff_byte_diff = {i: a for i, (a, b) in enumerate(zip(buff, buff_prev)) if a != b}

                # print({f'{i}': f'{a:02X}' for i, a in buff_byte_diff.items()})

                callbacks = list(dict.fromkeys([self.internal_callback_lut[k] for k in buff_byte_diff.keys() if k in self.internal_callback_lut]))
                for func in callbacks:
                    func(buff, buff_prev)

            buff_prev = buff

    def update(self, timeout_ms=1):
        buff = self.gamepad.read(max_length=64, timeout_ms=timeout_ms)  # why 64? meh

        if buff:
            # print(' '.join([f'{i:X}:{x:02X}' for i, x in enumerate(buff)]))

            # if buff_prev is None:
            #     print(' '.join([f'{i:X}:{x:02X}' for i, x in enumerate(buff)]))
            if self.buff_prev:
                buff_byte_diff = {i: a for i, (a, b) in enumerate(zip(buff, self.buff_prev)) if a != b}

                # print({f'{i}': f'{a:02X}' for i, a in buff_byte_diff.items()})

                callbacks = list(dict.fromkeys(
                    [self.internal_callback_lut[k] for k in buff_byte_diff.keys() if k in self.internal_callback_lut]))

                for func in callbacks:
                    func(buff, self.buff_prev)

            self.buff_prev = buff


    # Update Buttons
    def parse_byte5(self, buff, buff_prev):
        diff_byte = buff[5] ^ buff_prev[5]
        ext_callbacks_queue = {}

        # Decode DPAD
        if diff_byte & 0xF:
            prev_calls = {c: 0 for c in self.dpad_lut_callback_indices[buff_prev[5] & 0xF]}
            new_calls = {c: 1 for c in self.dpad_lut_callback_indices[buff[5] & 0xF]}
            # ext_callbacks_queue = prev_calls | new_calls
            ext_callbacks_queue = {**prev_calls, **new_calls}

            # print(f'callbacks_queue: {ext_callbacks_queue}')

        diff_byte_arr = reversed(f'{diff_byte >> 4:04b}')
        byte5_arr = reversed(f'{buff[5] >> 4:04b}')
        types = list(G29_JOY_INPUT_ENUM)[int(G29_JOY_INPUT_ENUM.BTN_SQUARE.value):]
        new_calls = {types[i]: v for i, (d, v) in enumerate(zip(diff_byte_arr, byte5_arr)) if d == '1'}
        # ext_callbacks_queue = ext_callbacks_queue | new_calls
        ext_callbacks_queue = {**ext_callbacks_queue, **new_calls}

        for input_code, value in ext_callbacks_queue.items():
            self.ext_callbacks[input_code](input_code, value)

        # print(f'parse byte 5 0b{diff_byte:08b} {ext_callbacks_queue}')

    def parse_byte6(self, buff, buff_prev):
        ext_callbacks_queue = {}
        diff_byte = buff[6] ^ buff_prev[6]

        diff_byte6_arr = reversed(f'{diff_byte:08b}')
        byte6_arr = reversed(f'{buff[6] :08b}')

        types = list(G29_JOY_INPUT_ENUM)[int(G29_JOY_INPUT_ENUM.BTN_L1.value):]
        ext_callbacks_queue = {types[i]: v for i, (d, v) in enumerate(zip(diff_byte6_arr, byte6_arr)) if d == '1'}

        for input_code, value in ext_callbacks_queue.items():
            self.ext_callbacks[input_code](input_code, value)

        # print(f'parse byte 6 0b{diff_byte:08b} {ext_callbacks_queue}')

    def parse_byte7(self, buff, buff_prev):
        diff_byte = buff[7] ^ buff_prev[7]
        if diff_byte & 0x1:
            bit_val = (buff[7] >> 0) & 1
            self.ext_callbacks[G29_JOY_INPUT_ENUM.BTN_SONY](G29_JOY_INPUT_ENUM.BTN_SONY, bit_val)

            # print(f'parse byte 7 0b{diff_byte:08b}')

    def parse_byte54(self, buff, buff_prev):
        data_byte = buff[54] & 0x1F
        diff_byte = (buff[54] ^ buff_prev[54]) & 0x1F

        diff_byte54_arr = reversed(f'{diff_byte:08b}')
        byte54_arr = reversed(f'{data_byte :08b}')

        types = list(G29_JOY_INPUT_ENUM)[int(G29_JOY_INPUT_ENUM.BTN_ENTER.value):]
        ext_callbacks_queue = {types[i]: v for i, (d, v) in enumerate(zip(diff_byte54_arr, byte54_arr)) if d == '1'}

        for input_code, value in ext_callbacks_queue.items():
            self.ext_callbacks[input_code](input_code, value)

        # print(f'parse byte 54 0b{diff_byte:08b} {ext_callbacks_queue}')

    # Update Axes
    def parse_axis_wheel(self, buff, buff_prev):
        # bytes 44:43
        axes = (struct.unpack("<H", bytes(buff[43:45]))[0]/(2**15 - 0.5) + -1) * -1
        axes = max(-1, min(axes, +1))
        self.ext_callbacks[G29_JOY_INPUT_ENUM.AXIS_WHEEL](G29_JOY_INPUT_ENUM.AXIS_WHEEL, axes)

        # print(f'update wheel position: {axes:8.4f}')

    def parse_axis_pedal_rht(self, buff, buff_prev):
        axes = 1 - ((struct.unpack("<H", bytes(buff[45:47]))[0]) / (2 ** 16-1))

        self.ext_callbacks[G29_JOY_INPUT_ENUM.AXIS_PEDAL_RHT](G29_JOY_INPUT_ENUM.AXIS_PEDAL_RHT, axes)
        # print(f'update pedal right: {axes:8.4f}')

    def parse_axis_pedal_mid(self, buff, buff_prev):
        axes = 1 - (struct.unpack("<H", bytes(buff[47:49]))[0]) / (2 ** 16-1)
        self.ext_callbacks[G29_JOY_INPUT_ENUM.AXIS_PEDAL_MID](G29_JOY_INPUT_ENUM.AXIS_PEDAL_MID, axes)
        # print(f'update pedal middle {axes:8.4f}')

    def parse_axis_pedal_lft(self, buff, buff_prev):
        axes = 1 - (struct.unpack("<H", bytes(buff[49:51]))[0]) / (2 ** 16-1)
        self.ext_callbacks[G29_JOY_INPUT_ENUM.AXIS_PEDAL_LFT](G29_JOY_INPUT_ENUM.AXIS_PEDAL_LFT, axes)
        # print(f'update pedal left {axes:8.4f}')

    @staticmethod
    def default_callback(input_code, val):
        if g29_joystick.isPrint:
            print(f'[{time.time():.6f}] Unhandled input code {input_code} = {val}')


def axis_wheel_handle(input_code, val):
    print(f'Wheel Position {val:8.3f}')


if __name__ == "__main__":
    joy = g29_joystick(isPrint=True)

    # joy.run()

    tEnd = time.time() + 50
    while time.time() < tEnd:
        joy.update()
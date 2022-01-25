from argparse import ArgumentParser
from json import loads
from pathlib import Path
from random import seed, sample
from typing import List


class Fialka:
    def __init__(self, config: dict):
        self.config = config

        self.seed = config.get('seed')
        self.alphabet_chars = config.get('alphabet_chars')
        self.operation = config.get('operation')
        self.entry_disc = config.get('entry_disc')
        self.reflector = config.get('reflector')
        self.keyboard_mapping = config.get('keyboard_mapping')
        self.rotors_wiring = config.get('rotors_wiring')
        self.daily_key = config.get('daily_key')
        self.message_key = config.get('message_key').copy() if config.get('message_key') else self.daily_key.get(
            'rotor_offsets').copy()
        self.pin_positions = config.get('pin_positions')
        self.encoding = config.get('encoding')
        self.encoder = config.get('encoder')

        seed(self.seed)
        self.punch_card = self.daily_key.get('punch_card') or self.random_punch_card()

        self.punch_card_inv = self.invert_array(self.punch_card)
        self.entry_disc_inv = self.invert_array(self.entry_disc)
        self.keyboard_mapping_inv = self.invert_array(self.keyboard_mapping)
        self.rotors_wiring_inv = self.invert_rotors_wiring(self.rotors_wiring)

        self.alphabet_length = len(self.alphabet_chars)

        self.encoded_words = []

        self.rotor_ruler_offset = 3  # page 111

    def encrypt(self, input_str: str):
        encoded_keyboard = [self.map_key(ch) for ch in input_str]

        encrypted = [self._encrypt(code) for code in encoded_keyboard]
        encoder = self.encoder.get(self.encoding)
        self.encoded_words.append([encoder[key] for key in encrypted])

        decoded_keyboard = [self.key_map(code) for code in encrypted]

        return ''.join(decoded_keyboard)

    # https://www.cryptomuseum.com/pub/files/Fialka_200.pdf
    def _encrypt(self, input: int):  # Page 92
        # The flow: keyboard > punch card > entry disc > +3 offset > 10 rotors
        # > -3 offset > reflector > +3 offset > 10 rotors inverse > -3 offset
        # > entry disc inverse > punch card inverse > keyboard inverse
        # > rotor stepping

        # The 'input' is a key-top char code

        # The direction of encryption starts from Keyboard through Entry Disc to
        # the Reflector and then it changes.
        dir_ed_to_ref = True

        # Key-top through keyboard wiring substitution
        ch = self.keyboard_mapping[input]

        # Punch Card substitution
        ch = self.punch_card[ch]

        # Entry Disk substitution
        ch = self.entry_disc[ch]

        # +3 offset, as described on page 111
        ch = (ch + self.rotor_ruler_offset) % self.alphabet_length

        # 10 rotors cycle from last (mostright to mostleft)
        for i in range(9, -1, -1):
            ch = self.handle_rotor(dir_ed_to_ref, i, ch)

        # -3 offset
        temp = ch - self.rotor_ruler_offset + self.alphabet_length
        ch = temp % self.alphabet_length

        # Reflector wiring (pairs of contacts, including Magic Circuit)
        ch = self.reflect(ch)

        # Change direction of signal
        dir_ed_to_ref = False

        # +3 offset
        ch = (ch + self.rotor_ruler_offset) % self.alphabet_length

        # Again, 10 rotors but from left to right
        for i in range(0, 10):
            ch = self.handle_rotor(dir_ed_to_ref, i, ch)

        # -3 offset
        temp = ch - self.rotor_ruler_offset + self.alphabet_length
        ch = temp % self.alphabet_length

        # Entry disc inverted
        ch = self.entry_disc_inv[ch]

        # Punch card inverted
        ch = self.punch_card_inv[ch]

        # Keyboard inverted
        ch = self.keyboard_mapping_inv[ch]

        # Advance rotors position
        self.step_rotors()

        return ch

    @staticmethod
    def random_punch_card():
        return sample(range(30), 30)

    @staticmethod
    def invert_array(arr: List[int]):
        output = [0] * len(arr)
        for idx, elem in enumerate(arr):
            output[elem] = idx
        return output

    def handle_rotor(self, dir_ed_to_ref, i, input):
        output = input + self.message_key[i]
        output = (output + self.alphabet_length) % self.alphabet_length
        if dir_ed_to_ref:
            output = self.rotors_wiring[i + 1][output]
        else:
            output = self.rotors_wiring_inv[i + 1][output]
        output -= self.message_key[i]
        output = (output + self.alphabet_length * 2) % self.alphabet_length
        return output

    def reflect(self, ch):
        return self.reflector[self.operation][ch]

    def step_rotors(self):
        for i in range(1, 10, 2):
            # Page 80
            check_position = (self.message_key[i] + 17) % self.alphabet_length
            self.message_key[i] = self.advance_rotor(i,
                                                     self.alphabet_length - 1)
            if self.pin_positions[i + 1][check_position] == 1:
                break

        for i in range(8, -1, -2):
            check_position = (self.message_key[i] + 20) % self.alphabet_length
            self.message_key[i] = self.advance_rotor(i)
            if self.pin_positions[i + 1][check_position] == 1:
                break

    def advance_rotor(self, i, offset=1):
        temp = self.message_key[i] + offset
        return temp % self.alphabet_length

    def map_key(self, c):
        if c == ' ':
            return 29
        return self.alphabet_chars.index(c)

    def key_map(self, i):
        return self.alphabet_chars[i]

    def invert_rotors_wiring(self, rotors_wiring: dict):
        return {
            key: self.invert_array(value) for key, value in
            rotors_wiring.items()
        }

    def add_offset(self, ch, offset):
        return (ch + offset) % self.alphabet_length

    def counter(self):
        chars_number = 0
        for word in self.encoded_words:
            chars_number += len(word)
        groups = chars_number // 5
        rest = chars_number % 5
        return groups, rest

    def decrypt(self, bitstream):
        self.reset_offsets()
        bit_words = [(bitstream[i:i + 5]) for i in range(0, len(bitstream), 5)]
        codes = [self.encoder[self.encoding].index(int(word, 2)) for word in
                 bit_words]
        decrypted = [self._encrypt(code) for code in codes]
        decoded_keyboard = [self.key_map(code) for code in decrypted]
        return ''.join(decoded_keyboard)

    def decrypt_text(self, ciphertext):
        self.reset_offsets()
        encoded_keyboard = [self.map_key(ch) for ch in ciphertext]
        decrypted = [self._encrypt(ch) for ch in encoded_keyboard]
        decoded_keyboard = [self.key_map(code) for code in decrypted]
        return ''.join(decoded_keyboard)

    def reset_offsets(self):
        self.message_key = self.config.get('message_key').copy() if self.config.get(
            'message_key') else self.daily_key.get('rotor_offsets').copy()

    def get_bitstream(self):
        bitstream = []
        for word in self.encoded_words:
            for char in word:
                bitstream.append(f'{char:05b}')
        return ''.join(bitstream)


def get_args():
    parser = ArgumentParser(description='Fialka simulator')
    parser.add_argument('--mode', choices=['encrypt', 'decrypt'], type=str,
                        required=True)
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--config', type=str, required=True)
    args = parser.parse_args()
    return args


def parse_config(config_path: str):
    config = loads(Path(config_path).read_bytes())

    rotos_wiring = config['rotors_wiring']
    converted = {int(k): v for k, v in rotos_wiring.items()}
    config['rotors_wiring'] = converted

    pin_positions = config['pin_positions']
    converted = {int(k): v for k, v in pin_positions.items()}
    config['pin_positions'] = converted

    return config


def main():
    args = get_args()
    config = parse_config(args.config)

    fialka = Fialka(config)

    print(f'Input text: {args.input}')

    if args.mode == 'encrypt':
        ciphered = fialka.encrypt(args.input)
        print(f'Encrypted text: {ciphered}')

        bitstream = fialka.get_bitstream()
        print(f'Radio transmission bits: {bitstream}')

    else:
        fialka.operation = 'decrypt'
        plain = fialka.decrypt(args.input)
        print(f'Decrypted from radio: {plain}')


if __name__ == '__main__':
    main()

# Fialka (M-125)

## Requirements

`python >=3.6`

## Usage

The required parameters are those:

* `--config <path>` e.g. _config/config.json_
* `--mode` possible parameters: {_encrypt_, _decrypt_}
* `--input` _TESTSTRING_

#### Encryption

`python main.py --config config/config.json --mode encrypt --input KRYPTOGRAFIA`

Output:
```text
Input text: KRYPTOGRAFIA
Encrypted text: BWHU7L8ANIBM
Radio transmission bits: 011001010000111000010111011110111110011010101101110110001001
```

#### Decryption

`python main.py --config config/config.json --mode decrypt --input 011001010000111000010111011110111110011010101101110110001001`

```text
Input text: 011001010000111000010111011110111110011010101101110110001001
Decrypted from radio: KRYPTOGRAFIA
```
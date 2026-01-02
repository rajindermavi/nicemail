
This library intentionally favors simplicity over maximal abstraction.
Credential models may combine static configuration and cached runtime state
to reduce persistence and usage complexity for small-scale use cases.

## paths.py

Provides function directing where files can be stored.

## models.py

MSalConfig is a dataclass for data relevant to using the MS Graph email service.

GoogleAPIConfig is a dataclass for data relevant to using the Google email API service.

KeyPolicy is to record policy for storing keys to encrypted data.

## store.py

SecureConfig is a class that saves the data in models.py encrypting the data.
KeyPolicy dictates how the data should be saved. 
If prefer_keyring == True, encrypt and save the key to the keyring.
If prefer_keyring == False or saving by keyring is not possible and allow_passphrase_fallback == True 
encrypt data with a key that must be provided by the user.
import json

from provider import (DecoderHolder, ImportedLocalReceiver, use_decoder,
                      use_decoder_holder, use_imported_local_receiver)


use_decoder(json.JSONDecoder())
use_decoder_holder(DecoderHolder(json.JSONDecoder()))
use_imported_local_receiver(ImportedLocalReceiver())

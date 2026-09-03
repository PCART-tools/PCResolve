import json

from provider import (DecoderHolder, ImportedLocalReceiver, use_decoder,
                      use_decoder_holder, use_imported_local_receiver,
                      use_cross_file_list, use_cross_file_text)


use_decoder(json.JSONDecoder())
cross_file_text = "cross file"
cross_file_items = []
use_cross_file_text(cross_file_text)
use_cross_file_list(cross_file_items)
use_decoder_holder(DecoderHolder(json.JSONDecoder()))
use_imported_local_receiver(ImportedLocalReceiver())

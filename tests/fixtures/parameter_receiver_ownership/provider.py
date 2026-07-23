def use_decoder(decoder):
    decoder.decode("cross-file")


def use_cross_file_text(text):
    text.swapcase()


def use_cross_file_list(items):
    items.reverse()


class DecoderHolder:
    def __init__(self, decoder):
        self.decoder = decoder


def use_decoder_holder(holder):
    decoder = holder.decoder
    decoder.decode("cross-file attribute")


class ImportedLocalReceiver:
    def ping(self):
        return True


def use_imported_local_receiver(receiver):
    receiver.ping()

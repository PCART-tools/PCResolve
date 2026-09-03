class TokenBuffer:
    def __init__(self):
        self.segments = []

    def add_segment(self):
        self.segments.append({"tokens": []})

    def append_token(self, value):
        for segment in self.segments:
            segment["tokens"].append(value)


def append_mixed(value):
    segments = [{"tokens": []}, value]
    for entry in segments:
        entry["tokens"].append(value)


def append_local(value):
    segments = []
    segments.append({"tokens": []})
    for local_entry in segments:
        local_entry["tokens"].append(value)


buffer = TokenBuffer()
buffer.add_segment()
buffer.append_token("word")
append_mixed({"tokens": []})
append_local("word")

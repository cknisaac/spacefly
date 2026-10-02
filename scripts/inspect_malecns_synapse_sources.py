"""Inspect public source schemas with generation-pinned HTTP range reads."""
import io
import json
import urllib.request

import pyarrow as pa


class RangeFile(io.RawIOBase):
    def __init__(self, url, size):
        self.url, self.length, self.pos = url, size, 0
        self.transferred = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = offset + (0 if whence == 0 else self.pos if whence == 1 else self.length)
        return self.pos

    def read(self, size=-1):
        size = min(self.length - self.pos, size if size >= 0 else self.length)
        if size <= 0:
            return b""
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{self.pos+size-1}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            if r.status != 206:
                raise ValueError(f"Expected partial response, got {r.status}")
            b = r.read()
        if len(b) != size:
            raise ValueError("Incomplete range")
        self.pos += size
        self.transferred += size
        return b


def main():
    prefix = "v1.0/connectome-data/flat-connectome/"
    meta_url = "https://storage.googleapis.com/storage/v1/b/flyem-male-cns/o?prefix=" + prefix
    with urllib.request.urlopen(meta_url, timeout=30) as r:
        items = json.load(r)["items"]
    for obj in items:
        name = obj["name"].split("/")[-1]
        if name not in ("syn-partners-male-cns-v1.0-minconf-0.5-traced-only.feather",
                        "syn-points-male-cns-v1.0-minconf-0.5.feather",
                        "tbar-neurotransmitters-male-cns-v1.0.feather"):
            continue
        url = "https://storage.googleapis.com/flyem-male-cns/" + obj["name"] + "?generation=" + obj["generation"]
        remote = RangeFile(url, int(obj["size"]))
        reader = pa.ipc.open_file(pa.PythonFile(remote))
        print(name, "batches", reader.num_record_batches, "bytes", obj["size"], flush=True)
        print(reader.schema, flush=True)
        batch = reader.get_batch(0)
        print("first_row", batch.slice(0, 1).to_pylist(), "transferred", remote.transferred, flush=True)


if __name__ == "__main__":
    main()

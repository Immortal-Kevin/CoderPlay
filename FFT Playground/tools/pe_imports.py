"""Read normal/delayed PE DLL imports with stdlib only; no binary is executed."""
import struct
from pathlib import Path


def dll_imports(path):
    data = Path(path).read_bytes()
    pe = struct.unpack_from("<I", data, 60)[0]
    if data[pe:pe+4] != b"PE\0\0":
        raise ValueError("Not a PE file")
    count, optional_size = struct.unpack_from("<H12xH", data, pe+6)
    optional = pe+24
    magic = struct.unpack_from("<H", data, optional)[0]
    directories = optional + (112 if magic == 0x20b else 96)
    section_start = optional+optional_size
    sections = [struct.unpack_from("<8sIIII", data, section_start+40*i) for i in range(count)]
    def offset(rva):
        for _, size, address, raw_size, raw_start in sections:
            if address <= rva < address+max(size,raw_size):
                return raw_start+rva-address
        return rva
    def string(rva):
        start=offset(rva)
        return data[start:data.index(b"\0",start)].decode("ascii")
    result=set()
    for index,size in [(1,20),(13,32)]:
        rva,length=struct.unpack_from("<II",data,directories+8*index)
        if not rva: continue
        start=offset(rva)
        for cursor in range(start,start+length,size):
            descriptor=data[cursor:cursor+size]
            if not any(descriptor): break
            name=struct.unpack_from("<I",descriptor,12 if index==1 else 4)[0]
            result.add(string(name).lower())
    return sorted(result)

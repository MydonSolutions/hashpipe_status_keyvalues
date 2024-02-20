import os
import ctypes

libhashpipe = None # set by `load_shared_hashpipe_lib`

from rao_keyvalue_property_mixin_classes.guppi_raw import GuppiRawProperties
from rao_keyvalue_property_mixin_classes.hpdaq_ata import HpdaqAtaProperties
from rao_keyvalue_property_mixin_classes.hpdaq_cosmic import HpdaqCosmicProperties
from rao_keyvalue_property_mixin_classes.hpdaq_meerkat import HpdaqMeerkatProperties


class HashpipeStatusBufferAta(dict, HpdaqAtaProperties, GuppiRawProperties):
    pass


class HashpipeStatusBufferCosmic(dict, HpdaqCosmicProperties, GuppiRawProperties):
    pass


class HashpipeStatusBufferMeerkat(dict, HpdaqMeerkatProperties, GuppiRawProperties):
    pass


PROPERTY_FGET_CLASS_MAP = {
    GuppiRawProperties.telescope.fget: {
        cls.telescope.fget(): cls
        for cls in [
            HashpipeStatusBufferAta,
            HashpipeStatusBufferCosmic,
            HashpipeStatusBufferMeerkat
        ]
    }
}


def auto_init_HashpipeStatusBuffer(keyvalues: dict):
    for property_fget, value_class_map in PROPERTY_FGET_CLASS_MAP.items():
        property_value = property_fget(keyvalues)
        if property_value in value_class_map:
            return value_class_map[property_value](**keyvalues)
    return keyvalues


class HashpipeStatusSharedMemoryIPC(ctypes.Structure):
    _fields_ = [
        ("instance_id", ctypes.c_int), # Instance ID of this status buffer (DO NOT SET/CHANGE!)
        ("shmid", ctypes.c_int), # Shared memory segment id
        ("lock", ctypes.c_void_p), # POSIX semaphore descriptor for locking
        ("buf", ctypes.POINTER(ctypes.c_char)), # Pointer to data area
    ]

    END_RECORD = "END" + " "*77

    def __init__(self, instance_id: int):
        assert libhashpipe is not None, f"libhashpipe.so has not been loaded, set 'HASHPIPE_SO_PATH' before importing, or call load_shared_hashpipe_lib before instantiating an instance of HashpipeStatus."
        rv = libhashpipe.hashpipe_status_attach(instance_id, ctypes.byref(self))
        if rv != 0:
            raise RuntimeError(f"Failed to connect to status buffer of instance {instance_id}")

    def __del__(self):
        if libhashpipe is None:
            return
        rv = libhashpipe.hashpipe_status_detach(ctypes.byref(self))
        if rv != 0:
            raise RuntimeError(f"Failed to detach from status buffer of instance {self.instance_id}")

    @staticmethod
    def _decode_value(v: str):
        try:
            try:
                return int(v)
            except ValueError:
                return float(v)
        except ValueError:
            # must be a str value, drop enclosing single-quotes
            v = v.strip()
            if v[0] == v[-1] == "'":
                return v[1:-1].strip()
        return v

    def parse_buffer(self):
        keyvalues = {}
        with self:
            i = 0
            while True:
                record = self.buf[i:i+80]
                try:
                    record = record.decode()
                except:
                    raise RuntimeError(f"Could not decode: {record}")
                if record == self.END_RECORD:
                    break
                key, value = record.split("=", maxsplit=1)
                keyvalues[key.strip()] = self._decode_value(value)
                i += 80
        return auto_init_HashpipeStatusBuffer(keyvalues)

    def __enter__(self):
        libhashpipe.hashpipe_status_lock(ctypes.byref(self))

    def __exit__(self, *args):
        libhashpipe.hashpipe_status_unlock(ctypes.byref(self))

HashpipeStatusSharedMemoryIPCPointer = ctypes.POINTER(HashpipeStatusSharedMemoryIPC)

def load_shared_hashpipe_lib(lib_so_path):
    global libhashpipe
    libhashpipe = ctypes.CDLL(lib_so_path)

    libhashpipe.hashpipe_status_key.argtypes = (ctypes.c_int, )
    libhashpipe.hashpipe_status_key.restypes = ctypes.c_int

    libhashpipe.hashpipe_status_attach.argtypes = (ctypes.c_int, HashpipeStatusSharedMemoryIPCPointer)
    libhashpipe.hashpipe_status_attach.restypes = ctypes.c_int

    libhashpipe.hashpipe_status_detach.argtypes = (HashpipeStatusSharedMemoryIPCPointer, )
    libhashpipe.hashpipe_status_detach.restypes = ctypes.c_int

    libhashpipe.hashpipe_status_lock.argtypes = (HashpipeStatusSharedMemoryIPCPointer, )
    libhashpipe.hashpipe_status_unlock.argtypes = (HashpipeStatusSharedMemoryIPCPointer, )

if (so_path := os.getenv("HASHPIPE_SO_PATH", None)) is not None:
    load_shared_hashpipe_lib(so_path)
elif (ld_library_path := os.getenv("LD_LIBRARY_PATH", None)) is not None:
    libfilename = os.getenv("HASHPIPE_SO_FILENAME", "libhashpipe.so")
    for lib_dirpath in ld_library_path.split(":"):
        if len(lib_dirpath) == 0:
            continue
        
        path = os.path.join(lib_dirpath, libfilename)
        if os.path.exists(path):
            load_shared_hashpipe_lib(path)
            break


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        load_shared_hashpipe_lib(sys.argv[-1])
    hs = HashpipeStatusSharedMemoryIPC(0)
    buffer = hs.parse_buffer()

    print(libhashpipe._name)
    print(type(buffer))
    print(buffer)
    print(buffer.pulse)

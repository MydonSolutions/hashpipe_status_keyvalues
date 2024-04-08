# Hashpipe Status Buffer

Hashpipe instantiates a FITS-style key-value status-buffer, in IPC shared memory.

This package uses `libhashpipe.so` to access (read-only at the moment) the status-buffer for a local instance, in particular tracking [this fork's branch](https://github.com/MydonSolutions/hashpipe/tree/seti).
The key-values are parsed into a dictionary, and properties from the appropriate [rao_keyvalue_property_mixin_classes](https://github.com/MydonSolutions/rao_keyvalue_property_mixin_classes) class are mixed-in.

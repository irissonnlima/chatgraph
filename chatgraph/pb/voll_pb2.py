# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: voll.proto
# Protobuf Python Version: 5.27.2
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    27,
    2,
    '',
    'voll.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\nvoll.proto\x12\x0bmessagevoll\"\xdb\x01\n\x0eMessageRequest\x12\x0f\n\x07hook_id\x18\x01 \x01(\t\x12\x15\n\renterprise_id\x18\x02 \x01(\t\x12\x1a\n\x12unique_customer_id\x18\x03 \x01(\t\x12\x15\n\rmessage_title\x18\x04 \x01(\t\x12\x14\n\x0cmessage_text\x18\x05 \x01(\t\x12\x17\n\x0fmessage_caption\x18\x06 \x01(\t\x12\x14\n\x0c\x62utton_title\x18\x07 \x01(\t\x12)\n\x07options\x18\x08 \x03(\x0b\x32\x18.messagevoll.QuickOption\"2\n\x0fMessageResponse\x12\x0e\n\x06status\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\"1\n\x0bQuickOption\x12\r\n\x05title\x18\x01 \x01(\t\x12\x13\n\x0b\x64\x65scription\x18\x02 \x01(\t2\xe7\x01\n\x0eMessageService\x12G\n\nSendButton\x12\x1b.messagevoll.MessageRequest\x1a\x1c.messagevoll.MessageResponse\x12\x45\n\x08SendList\x12\x1b.messagevoll.MessageRequest\x1a\x1c.messagevoll.MessageResponse\x12\x45\n\x08SendText\x12\x1b.messagevoll.MessageRequest\x1a\x1c.messagevoll.MessageResponseB\x12Z\x10./pb/messagevollb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'voll_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  _globals['DESCRIPTOR']._loaded_options = None
  _globals['DESCRIPTOR']._serialized_options = b'Z\020./pb/messagevoll'
  _globals['_MESSAGEREQUEST']._serialized_start=28
  _globals['_MESSAGEREQUEST']._serialized_end=247
  _globals['_MESSAGERESPONSE']._serialized_start=249
  _globals['_MESSAGERESPONSE']._serialized_end=299
  _globals['_QUICKOPTION']._serialized_start=301
  _globals['_QUICKOPTION']._serialized_end=350
  _globals['_MESSAGESERVICE']._serialized_start=353
  _globals['_MESSAGESERVICE']._serialized_end=584
# @@protoc_insertion_point(module_scope)

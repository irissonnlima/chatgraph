# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: router.proto
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
    'router.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0crouter.proto\x12\x07\x63hatbot\"\x06\n\x04Void\"0\n\rRequestStatus\x12\x0e\n\x06status\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\"-\n\x06\x43hatID\x12\x0f\n\x07user_id\x18\x01 \x01(\t\x12\x12\n\ncompany_id\x18\x02 \x01(\t\"q\n\tUserState\x12 \n\x07\x63hat_id\x18\x01 \x01(\x0b\x32\x0f.chatbot.ChatID\x12\x0c\n\x04menu\x18\x02 \x01(\t\x12\r\n\x05route\x18\x03 \x01(\t\x12\x10\n\x08protocol\x18\x04 \x01(\t\x12\x13\n\x0bobservation\x18\x05 \x01(\t\"8\n\rUserStateList\x12\'\n\x0buser_states\x18\x01 \x03(\x0b\x32\x12.chatbot.UserState\"j\n\x0bTextMessage\x12\x0c\n\x04type\x18\x01 \x01(\t\x12\x0b\n\x03url\x18\x02 \x01(\t\x12\x10\n\x08\x66ilename\x18\x03 \x01(\t\x12\r\n\x05title\x18\x04 \x01(\t\x12\x0e\n\x06\x64\x65tail\x18\x05 \x01(\t\x12\x0f\n\x07\x63\x61ption\x18\x06 \x01(\t\"5\n\x06\x42utton\x12\x0c\n\x04type\x18\x01 \x01(\t\x12\r\n\x05title\x18\x02 \x01(\t\x12\x0e\n\x06\x64\x65tail\x18\x03 \x01(\t\"\x9d\x01\n\x07Message\x12 \n\x07\x63hat_id\x18\x01 \x01(\x0b\x32\x0f.chatbot.ChatID\x12%\n\x07message\x18\x02 \x01(\x0b\x32\x14.chatbot.TextMessage\x12 \n\x07\x62uttons\x18\x03 \x03(\x0b\x32\x0f.chatbot.Button\x12\'\n\x0e\x64isplay_button\x18\x04 \x01(\x0b\x32\x0f.chatbot.Button\"O\n\x16TransferToHumanRequest\x12 \n\x07\x63hat_id\x18\x01 \x01(\x0b\x32\x0f.chatbot.ChatID\x12\x13\n\x0b\x63\x61mpaign_id\x18\x02 \x01(\t\"]\n\x15TransferToMenuRequest\x12 \n\x07\x63hat_id\x18\x01 \x01(\x0b\x32\x0f.chatbot.ChatID\x12\x0c\n\x04menu\x18\x02 \x01(\t\x12\x14\n\x0cuser_message\x18\x03 \x01(\t\"\x1e\n\x0eTabulationName\x12\x0c\n\x04name\x18\x01 \x01(\t\"B\n\x11TabulationDetails\x12\n\n\x02id\x18\x01 \x01(\t\x12\x0c\n\x04name\x18\x02 \x01(\t\x12\x13\n\x0blast_update\x18\x03 \x01(\t\"B\n\x0fTabulationsList\x12/\n\x0btabulations\x18\x01 \x03(\x0b\x32\x1a.chatbot.TabulationDetails\"I\n\x0e\x45ndChatRequest\x12 \n\x07\x63hat_id\x18\x01 \x01(\x0b\x32\x0f.chatbot.ChatID\x12\x15\n\rtabulation_id\x18\x02 \x01(\t\"\x1c\n\x0c\x43\x61mpaignName\x12\x0c\n\x04name\x18\x01 \x01(\t\"@\n\x0f\x43\x61mpaignDetails\x12\n\n\x02id\x18\x01 \x01(\t\x12\x0c\n\x04name\x18\x02 \x01(\t\x12\x13\n\x0blast_update\x18\x03 \x01(\t\"<\n\rCampaignsList\x12+\n\tcampaigns\x18\x01 \x03(\x0b\x32\x18.chatbot.CampaignDetails2\x83\x02\n\x10UserStateService\x12\x43\n\x15InsertUpdateUserState\x12\x12.chatbot.UserState\x1a\x16.chatbot.RequestStatus\x12:\n\x0f\x44\x65leteUserState\x12\x0f.chatbot.ChatID\x1a\x16.chatbot.RequestStatus\x12\x33\n\x0cGetUserState\x12\x0f.chatbot.ChatID\x1a\x12.chatbot.UserState\x12\x39\n\x10GetAllUserStates\x12\r.chatbot.Void\x1a\x16.chatbot.UserStateList2F\n\x0bSendMessage\x12\x37\n\x0bSendMessage\x12\x10.chatbot.Message\x1a\x16.chatbot.RequestStatus2\x9c\x02\n\x08Transfer\x12\x38\n\x0fGetAllCampaigns\x12\r.chatbot.Void\x1a\x16.chatbot.CampaignsList\x12@\n\rGetCampaignID\x12\x15.chatbot.CampaignName\x1a\x18.chatbot.CampaignDetails\x12J\n\x0fTransferToHuman\x12\x1f.chatbot.TransferToHumanRequest\x1a\x16.chatbot.RequestStatus\x12H\n\x0eTransferToMenu\x12\x1e.chatbot.TransferToMenuRequest\x1a\x16.chatbot.RequestStatus2\xcb\x01\n\x07\x45ndChat\x12<\n\x11GetAllTabulations\x12\r.chatbot.Void\x1a\x18.chatbot.TabulationsList\x12\x46\n\x0fGetTabulationID\x12\x17.chatbot.TabulationName\x1a\x1a.chatbot.TabulationDetails\x12:\n\x07\x45ndChat\x12\x17.chatbot.EndChatRequest\x1a\x16.chatbot.RequestStatusB\x0bZ\t./chatbotb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'router_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  _globals['DESCRIPTOR']._loaded_options = None
  _globals['DESCRIPTOR']._serialized_options = b'Z\t./chatbot'
  _globals['_VOID']._serialized_start=25
  _globals['_VOID']._serialized_end=31
  _globals['_REQUESTSTATUS']._serialized_start=33
  _globals['_REQUESTSTATUS']._serialized_end=81
  _globals['_CHATID']._serialized_start=83
  _globals['_CHATID']._serialized_end=128
  _globals['_USERSTATE']._serialized_start=130
  _globals['_USERSTATE']._serialized_end=243
  _globals['_USERSTATELIST']._serialized_start=245
  _globals['_USERSTATELIST']._serialized_end=301
  _globals['_TEXTMESSAGE']._serialized_start=303
  _globals['_TEXTMESSAGE']._serialized_end=409
  _globals['_BUTTON']._serialized_start=411
  _globals['_BUTTON']._serialized_end=464
  _globals['_MESSAGE']._serialized_start=467
  _globals['_MESSAGE']._serialized_end=624
  _globals['_TRANSFERTOHUMANREQUEST']._serialized_start=626
  _globals['_TRANSFERTOHUMANREQUEST']._serialized_end=705
  _globals['_TRANSFERTOMENUREQUEST']._serialized_start=707
  _globals['_TRANSFERTOMENUREQUEST']._serialized_end=800
  _globals['_TABULATIONNAME']._serialized_start=802
  _globals['_TABULATIONNAME']._serialized_end=832
  _globals['_TABULATIONDETAILS']._serialized_start=834
  _globals['_TABULATIONDETAILS']._serialized_end=900
  _globals['_TABULATIONSLIST']._serialized_start=902
  _globals['_TABULATIONSLIST']._serialized_end=968
  _globals['_ENDCHATREQUEST']._serialized_start=970
  _globals['_ENDCHATREQUEST']._serialized_end=1043
  _globals['_CAMPAIGNNAME']._serialized_start=1045
  _globals['_CAMPAIGNNAME']._serialized_end=1073
  _globals['_CAMPAIGNDETAILS']._serialized_start=1075
  _globals['_CAMPAIGNDETAILS']._serialized_end=1139
  _globals['_CAMPAIGNSLIST']._serialized_start=1141
  _globals['_CAMPAIGNSLIST']._serialized_end=1201
  _globals['_USERSTATESERVICE']._serialized_start=1204
  _globals['_USERSTATESERVICE']._serialized_end=1463
  _globals['_SENDMESSAGE']._serialized_start=1465
  _globals['_SENDMESSAGE']._serialized_end=1535
  _globals['_TRANSFER']._serialized_start=1538
  _globals['_TRANSFER']._serialized_end=1822
  _globals['_ENDCHAT']._serialized_start=1825
  _globals['_ENDCHAT']._serialized_end=2028
# @@protoc_insertion_point(module_scope)

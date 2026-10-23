"""Check references, control flow and the actual encoded HTTP request."""
import json
import pathlib
import plistlib

root = pathlib.Path(__file__).resolve().parents[1]
p = plistlib.loads((root / "dist/Snap2Cal.unsigned.shortcut").read_bytes())
actions = p["WFWorkflowActions"]
seen, stack, urls = set(), [], []


def inspect(value):
    if isinstance(value, dict):
        if "OutputUUID" in value:
            assert value["OutputUUID"] in seen, f"Unresolved output: {value}"
        if value.get("WFSerializationType") == "WFTextTokenString":
            obj = value["Value"]
            raw = obj["string"].encode("utf-16-le")
            for key in obj.get("attachmentsByRange", {}):
                pos = int(key.split(",")[0].lstrip("{"))
                assert raw[pos*2:pos*2+2] == "\ufffc".encode("utf-16-le")
        for v in value.values(): inspect(v)
    elif isinstance(value, list):
        for v in value: inspect(v)


for action in actions:
    params = action["WFWorkflowActionParameters"]
    inspect(params)
    ident = action["WFWorkflowActionIdentifier"]
    if "WFControlFlowMode" in params:
        mode, group = params["WFControlFlowMode"], params["GroupingIdentifier"]
        if mode == 0: stack.append((ident, group))
        elif mode == 2: assert stack.pop() == (ident, group)
        else: assert stack[-1] == (ident, group)
    if ident.endswith("downloadurl"): urls.append(params["WFURL"])
    seen.add(params["UUID"])
assert not stack
assert not any(x["WFWorkflowActionIdentifier"].endswith(".date") and x["WFWorkflowActionIdentifier"]=="is.workflow.actions.date" for x in actions), "Do not force raw target text into a Date action"
pickers = [x["WFWorkflowActionParameters"] for x in actions if x["WFWorkflowActionIdentifier"].endswith("ask") and x["WFWorkflowActionParameters"].get("WFInputType")=="Date and Time"]
assert not pickers, "Missing dates must be edited in the calendar form, without separate date prompts"
for action in actions:
    params = action["WFWorkflowActionParameters"]
    if action["WFWorkflowActionIdentifier"].endswith("conditional") and params.get("WFControlFlowMode")==0:
        code = params["WFCondition"]
        if code in (4,5):
            assert params["WFConditionalActionString"]["Value"]["string"] == "stop"
            assert params["WFInput"]["Variable"]["Value"]["Aggrandizements"][-1]["CoercionItemClass"] == "WFStringContentItem"
        if code == 2:
            assert params["WFInput"]["Variable"]["Value"]["Aggrandizements"][-1]["CoercionItemClass"] == "WFNumberContentItem"
assert urls == ["https://api.deepseek.com/chat/completions"]
assert not any(x["WFWorkflowActionIdentifier"].endswith("askllm") for x in actions)
assert "ActionExtension" in p["WFWorkflowTypes"]
assert "WFImageContentItem" in p["WFWorkflowInputContentItemClasses"]
assert p["WFWorkflowHasShortcutInputVariables"] is True
formatter = next(x["WFWorkflowActionParameters"] for x in actions if x["WFWorkflowActionIdentifier"].endswith("format.date"))
assert formatter["WFDateFormatStyle"] == "Custom"
assert formatter["WFDateFormat"] == "yyyy年M月d日 HH:mm"
assert formatter["WFDate"]["WFSerializationType"] == "WFTextTokenString"
formatter_index = next(i for i,x in enumerate(actions) if x["WFWorkflowActionParameters"]["UUID"] == formatter["UUID"])
assert formatter_index < next(i for i,x in enumerate(actions) if x["WFWorkflowActionIdentifier"].endswith("choosefromlist"))
ocr = next(x["WFWorkflowActionParameters"] for x in actions if x["WFWorkflowActionIdentifier"].endswith("extracttextfromimage"))
assert "WFInput" not in ocr, "OCR uses WFImage, not the generic WFInput key"
assert ocr["WFImage"]["Value"] == {"Type":"Variable", "VariableName":"待识别图片"}
input_params = actions[1]["WFWorkflowActionParameters"]
assert input_params["WFInput"]["Variable"]["Value"]["Type"] == "ExtensionInput"
input_group = input_params["GroupingIdentifier"]
branch_index = next(i for i,x in enumerate(actions) if x["WFWorkflowActionParameters"].get("GroupingIdentifier")==input_group and x["WFWorkflowActionParameters"].get("WFControlFlowMode")==1)
end_index = next(i for i,x in enumerate(actions) if x["WFWorkflowActionParameters"].get("GroupingIdentifier")==input_group and x["WFWorkflowActionParameters"].get("WFControlFlowMode")==2)
shot_index = next(i for i,x in enumerate(actions) if x["WFWorkflowActionIdentifier"].endswith("takescreenshot"))
assert branch_index < shot_index < end_index, "Screenshot must only run when no image was shared"
shared_store = next(x["WFWorkflowActionParameters"] for x in actions[2:branch_index] if x["WFWorkflowActionIdentifier"].endswith("setvariable"))
shot_store = actions[shot_index+1]["WFWorkflowActionParameters"]
assert shared_store["WFVariableName"] == shot_store["WFVariableName"] == "待识别图片"
assert shot_index < next(i for i,x in enumerate(actions) if x["WFWorkflowActionIdentifier"].endswith("ask"))


def decode_text(value):
    assert value["WFSerializationType"] == "WFTextTokenString"
    return value["Value"]["string"].replace("\ufffc", '测试文字："标题"\\换行\n')


def decode_fields(value):
    result = {}
    for item in value["Value"]["WFDictionaryFieldValueItems"]:
        kind, v = item["WFItemType"], item["WFValue"]
        result[decode_text(item["WFKey"])] = decode_value(kind, v)
    return result


def decode_value(kind, value):
    if kind == 0: return decode_text(value)
    if kind == 1: return decode_fields(value["Value"])
    if kind == 2: return [decode_value(x["WFItemType"], x["WFValue"]) for x in value["Value"]]
    if kind == 3: return int(decode_text(value))
    raise AssertionError(kind)


request = next(x["WFWorkflowActionParameters"] for x in actions if x["WFWorkflowActionIdentifier"].endswith("downloadurl"))
body = decode_fields(request["WFJSONValues"])
assert body["max_tokens"] == 8192
assert [x["type"] for x in body["messages"][1]["content"]] == ["text", "image_url"]
assert body["response_format"] == {"type": "json_object"}
assert body["thinking"] == {"type": "disabled"}
assert [x["role"] for x in body["messages"]] == ["system", "user"]
assert json.loads(json.dumps(body)) == body
event = next(x["WFWorkflowActionParameters"] for x in actions if x["WFWorkflowActionIdentifier"].endswith("addnewevent"))
assert event["ShowWhenRun"] is True
assert all(x["WFWorkflowActionParameters"]["ShowWhenRun"] is True for x in actions if x["WFWorkflowActionIdentifier"].endswith("addnewevent"))
chooser = next(x["WFWorkflowActionParameters"] for x in actions if x["WFWorkflowActionIdentifier"].endswith("choosefromlist"))
assert chooser["WFChooseFromListActionSelectMultiple"] is True
assert chooser["WFChooseFromListActionSelectAll"] is False
creation_loop = [x["WFWorkflowActionParameters"] for x in actions if x["WFWorkflowActionIdentifier"].endswith("repeat.each") and x["WFWorkflowActionParameters"]["WFControlFlowMode"]==0][-1]
assert creation_loop["WFInput"]["Value"]["OutputUUID"] == chooser["UUID"]
assert event["WFAlertTime"] == "1 hour before"
assert "WFAlertCustomTime" not in event
assert "WFCalendarDescriptor" not in event
assert "WFCalendarItemCalendar" not in event
assert len(p["WFWorkflowImportQuestions"])==5
assert not any(x["WFWorkflowActionIdentifier"].endswith("addnewreminder") for x in actions)
assert not any(x["WFWorkflowActionParameters"].get("WFAlertActionTitle")=="发送到 DeepSeek" for x in actions)
assert any(q["ParameterKey"]=="WFAlertTime" and q["DefaultValue"]=="1 hour before" for q in p["WFWorkflowImportQuestions"])
for q in p["WFWorkflowImportQuestions"]:
    assert q["ParameterKey"] in actions[q["ActionIndex"]]["WFWorkflowActionParameters"] or q["ParameterKey"]=="WFCalendarDescriptor"
    if q["ParameterKey"]=="WFCalendarDescriptor":
        assert q["ParameterKey"] not in actions[q["ActionIndex"]]["WFWorkflowActionParameters"]
        assert "DefaultValue" not in q
    if "API Key" in q["Text"]: assert q["DefaultValue"] == ""
print(f"PASS: {len(actions)} actions, ordered references, balanced control flow, DeepSeek-only request, JSON encoding, editable calendar forms after multi-selection, calendar-only relative first alert, no Reminders writes and empty API key.")

request_index = next(i for i,x in enumerate(actions) if x["WFWorkflowActionIdentifier"].endswith("downloadurl"))
request_uuid = actions[request_index]["WFWorkflowActionParameters"]["UUID"]
choice_get = next(i for i,x in enumerate(actions) if x["WFWorkflowActionIdentifier"].endswith("getvalueforkey") and x["WFWorkflowActionParameters"].get("WFDictionaryKey")=="choices")
first_choice = next(i for i,x in enumerate(actions[choice_get+1:],choice_get+1) if x["WFWorkflowActionIdentifier"].endswith("getitemfromlist"))
assert any(x["WFWorkflowActionIdentifier"].endswith("exit") for x in actions[choice_get+1:first_choice]), "Empty choices must stop before indexing"
assert any(x["WFWorkflowActionIdentifier"].endswith("image.convert") and x["WFWorkflowActionParameters"].get("WFImageFormat")=="PNG" for x in actions[:request_index])
assert not any(x["WFWorkflowActionIdentifier"].endswith("exit") for x in actions[next(i for i,x in enumerate(actions) if x["WFWorkflowActionIdentifier"].endswith("extracttextfromimage"))+1:next(i for i,x in enumerate(actions) if x["WFWorkflowActionParameters"].get("CustomOutputName")=="DeepSeek API Key")]), "OCR-empty must not block the vision model"
assert not (root/"tools/build_shortcut.py").read_text().count('reference/'), "Release builder must not depend on private or third-party reference files"
print("PASS: input and API-response guards, PNG upload, OCR fallback and self-contained build.")

for action in actions:
    if action["WFWorkflowActionIdentifier"].endswith("text.replace"):
        q = action["WFWorkflowActionParameters"]
        assert q["WFInput"]["WFSerializationType"] == "WFTextTokenString", "Replace Text expects a text token string; attachments lose the input in native Shortcuts"
        assert len(q["WFInput"]["Value"]["attachmentsByRange"]) == 1
print("PASS: Replace Text uses the native text-field serialization, including API-key input.")

"""Evaluate the generated event-loop wiring with fixed model responses.

This is a local data-flow check, not an iPhone/LLM integration test.
"""
import datetime as dt
import pathlib
import plistlib
import re

p = plistlib.loads((pathlib.Path(__file__).resolve().parents[1] / "dist/Snap2Cal.unsigned.shortcut").read_bytes())
all_actions = p["WFWorkflowActions"]
loop_start = [i for i,a in enumerate(all_actions) if a["WFWorkflowActionIdentifier"].endswith("repeat.each") and a["WFWorkflowActionParameters"]["WFControlFlowMode"]==0][-1]
source_events_uuid = next(a["WFWorkflowActionParameters"]["WFInput"]["Value"]["OutputUUID"] for a in all_actions[loop_start:] if a["WFWorkflowActionIdentifier"].endswith("getitemfromlist") and a["WFWorkflowActionParameters"].get("WFItemSpecifier")=="Item At Index")
loop_group = all_actions[loop_start]["WFWorkflowActionParameters"]["GroupingIdentifier"]
loop_end = next(i for i,a in enumerate(all_actions) if a["WFWorkflowActionParameters"].get("GroupingIdentifier")==loop_group and a["WFWorkflowActionParameters"].get("WFControlFlowMode")==2)
actions = all_actions[loop_start+1:loop_end]
now = dt.datetime.fromisoformat("2026-10-23T10:00:00+08:00")


def run(items, edited_end=None, picked_date=None, selected_indices=None, settings=None, chosen_calendar="用户选择的日历"):
    outputs, variables, events, reminders = {source_events_uuid:items}, {}, [], []
    for action in all_actions:
        if action["WFWorkflowActionIdentifier"].endswith("number"):
            q=action["WFWorkflowActionParameters"]
            outputs[q["UUID"]] = (settings or {}).get(q["CustomOutputName"],float(q["WFNumberActionNumber"]))

    def resolve(value):
        if not isinstance(value, dict): return value
        if value.get("WFSerializationType") == "WFTextTokenAttachment": return resolve(value["Value"])
        if value.get("WFSerializationType") == "WFTextTokenString":
            obj = value["Value"]
            refs = obj.get("attachmentsByRange", {})
            if obj["string"] == "\ufffc": return resolve(next(iter(refs.values())))
            result = obj["string"].encode("utf-16-le")
            for key, ref in sorted(refs.items(), key=lambda kv:int(kv[0].split(",")[0][1:]), reverse=True):
                offset = int(key.split(",")[0][1:])*2
                result = result[:offset]+str(resolve(ref)).encode("utf-16-le")+result[offset+2:]
            return result.decode("utf-16-le")
        kind = value.get("Type")
        if kind == "CurrentDate": return now
        if kind == "ActionOutput": return outputs[value["OutputUUID"]]
        if kind == "Variable" and "VariableName" in value: return variables[value["VariableName"]]
        if kind == "Variable": return resolve(value["Variable"])
        return value

    def date(value):
        result = resolve(value)
        parsed_date = result if isinstance(result,dt.datetime) else dt.datetime.fromisoformat(result)
        return parsed_date if parsed_date.tzinfo else parsed_date.replace(tzinfo=now.tzinfo)

    for item_index in (range(1,len(items)+1) if selected_indices is None else selected_indices):
        item = items[item_index-1]
        variables["Repeat Item"] = f"{item_index}. {item['title']}\n时间：{item.get('target','未明确')}"
        index = 0
        while index < len(actions):
            action = actions[index]
            name = action["WFWorkflowActionIdentifier"].split("is.workflow.actions.")[-1]
            q = action["WFWorkflowActionParameters"]
            output = None
            if name == "conditional":
                group, mode = q["GroupingIdentifier"], q["WFControlFlowMode"]
                if mode == 0:
                    value = resolve(q["WFInput"])
                    condition = q["WFCondition"]
                    matched = bool(value) if condition == 100 else not bool(value) if condition == 101 else value < q["WFNumberValue"] if condition == 0 else value > q["WFNumberValue"]
                    if not matched:
                        index = next(j for j in range(index+1,len(actions)) if actions[j]["WFWorkflowActionParameters"].get("GroupingIdentifier")==group and actions[j]["WFWorkflowActionParameters"].get("WFControlFlowMode") in (1,2))
                elif mode == 1:
                    index = next(j for j in range(index+1,len(actions)) if actions[j]["WFWorkflowActionParameters"].get("GroupingIdentifier")==group and actions[j]["WFWorkflowActionParameters"].get("WFControlFlowMode")==2)
            elif name == "detect.dictionary": output = resolve(q["WFInput"])
            elif name == "getvalueforkey": output = resolve(q["WFInput"]).get(q["WFDictionaryKey"], "")
            elif name == "text.replace":
                value=resolve(q["WFInput"])
                output=re.sub(q["WFReplaceTextFind"],q["WFReplaceTextReplace"],"" if value is None else str(value))
            elif name == "text.match":
                value = resolve(q["text"])
                output = re.findall(q["WFMatchTextPattern"], "" if value is None else str(value))
            elif name == "detect.date":
                output = []
                values = resolve(q["WFInput"])
                for value in values:
                    try: output.append(dt.datetime.fromisoformat(value.strip().replace("Z","+00:00")))
                    except ValueError: pass
            elif name == "count": output = len(resolve(q["Input"]))
            elif name == "getitemfromlist":
                index_value = int(resolve(q["WFItemIndex"]))-1 if q["WFItemSpecifier"]=="Item At Index" else 0
                output = resolve(q["WFInput"])[index_value]
            elif name == "ask":
                assert q["WFInputType"] == "Date and Time"
                assert picked_date is not None, "Missing date must open a picker"
                output = picked_date
            elif name == "gettext": output = resolve(q["WFTextActionText"])
            elif name == "setvariable": variables[q["WFVariableName"]] = resolve(q["WFInput"])
            elif name == "date": output = date(q["WFDateActionDate"])
            elif name == "adjustdate":
                amount = q["WFDuration"]["Value"]
                delta = dt.timedelta(seconds=resolve(amount["Magnitude"])*{"min":60,"hour":3600}[amount["Unit"]])
                output = date(q["WFDate"]) + (delta if q["WFAdjustOperation"]=="Add" else -delta)
            elif name == "format.date":
                assert q["WFDateFormat"] == "yyyy-MM-dd HH:mm"
                output = date(q["WFDate"]).astimezone(now.tzinfo).strftime("%Y-%m-%d %H:%M")
            elif name == "addnewevent":
                output = {"Title":resolve(q["WFCalendarItemTitle"]), "Start Date":date(q["WFCalendarItemStartDate"]), "End Date":edited_end or date(q["WFCalendarItemEndDate"]), "Alert":date(q["WFCalendarItemStartDate"])-dt.timedelta(hours=1), "Calendar":chosen_calendar, "Has Alarms":True}
                events.append(output)
            elif name == "properties.calendarevents": output = resolve(q["WFInput"])[q["WFContentItemPropertyName"]]
            elif name == "gettimebetweendates": output = (date(q["WFInput"])-date(q["WFTimeUntilFromDate"])).total_seconds()
            elif name == "addnewreminder": reminders.append({"title":resolve(q["WFCalendarItemTitle"]), "at":date(q["WFAlertCustomTime"])})
            elif name == "alert": pass
            else: raise AssertionError(f"Unhandled action {name}")
            outputs[q["UUID"]] = output
            index += 1
    return events, reminders


fixtures = [
    {"title":"【截止】提交材料", "target":"2026-10-24T18:00:00+08:00", "location":"", "notes":"24日18点提交材料"},
    {"title":"项目会议", "target":"2026-10-25T09:00:00+08:00", "location":"会议室", "notes":"25日9点项目会议"},
]
events, reminders = run(fixtures)
assert not reminders
for item,event in zip(fixtures,events):
    target=dt.datetime.fromisoformat(item["target"])
    assert event["Title"]==item["title"]
    assert event["Start Date"]==target-dt.timedelta(minutes=15)
    assert event["End Date"]==target
    assert event["Alert"]==event["Start Date"]-dt.timedelta(hours=1)
three=[fixtures[0],{"title":"跳过的无时间通知","target":"","notes":"","location":""},fixtures[1]]
selected,reminders=run(three,selected_indices=[1,3])
assert [x["Title"] for x in selected]==[fixtures[0]["title"],fixtures[1]["title"]]
assert not reminders
assert run(three,selected_indices=[])==([],[])
for invalid in [None,"","  ","null","未提及","2026-10-24","2026-02-31T12:00:00+08:00"]:
    draft,_=run([{**fixtures[0],"target":invalid}])
    assert draft[0]["End Date"]==now
    assert draft[0]["Title"].startswith("【时间待确认】")
custom,_=run([fixtures[0]],settings={"日程提前分钟数":30},chosen_calendar="个人")
assert custom[0]["Start Date"]==dt.datetime.fromisoformat(fixtures[0]["target"])-dt.timedelta(minutes=30)
assert custom[0]["Calendar"]=="个人"
print("PASS: independent notices, selection/skip, missing-time draft, configurable duration/calendar, relative 1-hour first alert and no Reminders creation. Second alert is a manual calendar-form step.")

for title_value in ["", "  ", None, "🙂会议|第二行\n内容"]:
    title_case,_=run([{**fixtures[0],"title":title_value}])
    expected_title = (str(title_value).strip() if title_value is not None else "") or "未命名事项（请补充标题）"
    assert title_case[0]["Title"] == expected_title
for date_value in ["2028-02-29T00:05:00+08:00","2026-12-31T23:59:00Z","2027-01-01T00:00:00-05:00"]:
    date_case,_=run([{**fixtures[0],"target":date_value}])
    assert date_case[0]["End Date"]==dt.datetime.fromisoformat(date_value.replace("Z","+00:00"))
    assert date_case[0]["End Date"]-date_case[0]["Start Date"]==dt.timedelta(minutes=15)
print("PASS: blank/null/emoji/multiline titles, leap day, year crossing and explicit UTC/time-zone offsets. Local simulation only.")

for bad_date in ["2026-02-29T10:00:00+08:00", "2028-02-30T10:00:00+08:00", "2026-04-31T10:00:00+08:00", "2026-10-24T24:00:00+08:00", "2026-10-24T10:00:00+14:30", "0000-01-01T10:00:00Z", "明天下午", "", None]:
    draft, _ = run([{**fixtures[0], "target":bad_date}])
    assert draft[0]["End Date"] == now
    assert draft[0]["Title"].startswith("【时间待确认】")
print("PASS: impossible calendar dates, invalid time/offset, free text and missing values become editable drafts in the simulation.")

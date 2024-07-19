from dataclasses import fields

def dataclassFromDict(className, argDict):
    """Helper method to convert a dict to a dataclass instance"""
    fieldSet = {f.name for f in fields(className) if f.init}
    filteredArgDict = {k : v for k, v in argDict.items() if k in fieldSet}
    return className(**filteredArgDict)
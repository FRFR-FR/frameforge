extends Node
class_name GameForgeInventory
signal inventory_changed(items: Dictionary)
@export var capacity := 24
var items: Dictionary = {}

func add_item(item_id: String, amount: int = 1) -> bool:
    if item_id.is_empty() or amount <= 0:
        return false
    var total := 0
    for count in items.values():
        total += int(count)
    if not items.has(item_id) and total >= capacity:
        return false
    items[item_id] = int(items.get(item_id, 0)) + amount
    inventory_changed.emit(items.duplicate(true))
    return true

func remove_item(item_id: String, amount: int = 1) -> bool:
    if amount <= 0 or int(items.get(item_id, 0)) < amount:
        return false
    items[item_id] = int(items[item_id]) - amount
    if items[item_id] <= 0:
        items.erase(item_id)
    inventory_changed.emit(items.duplicate(true))
    return true

func count(item_id: String) -> int:
    return int(items.get(item_id, 0))

func serialize() -> Dictionary:
    return items.duplicate(true)

func restore(data: Dictionary) -> void:
    items.clear()
    for key in data:
        if int(data[key]) > 0 and items.size() < capacity:
            items[str(key)] = int(data[key])
    inventory_changed.emit(items.duplicate(true))

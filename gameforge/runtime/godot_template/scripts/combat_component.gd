extends Node
class_name GameForgeCombatComponent
signal health_changed(current: float, maximum: float)
signal defeated
@export var max_health: float = 100.0
@export var invulnerability_seconds: float = 0.35
var health: float
var invulnerability_left := 0.0
var defeated_state := false

func _ready() -> void:
    health = max_health

func _process(delta: float) -> void:
    invulnerability_left = maxf(0.0, invulnerability_left - delta)

func apply_damage(amount: float) -> void:
    if defeated_state or invulnerability_left > 0.0 or amount <= 0.0:
        return
    health = maxf(0.0, health - amount)
    invulnerability_left = invulnerability_seconds
    health_changed.emit(health, max_health)
    if health <= 0.0:
        defeated_state = true
        defeated.emit()

func heal(amount: float) -> void:
    if defeated_state or amount <= 0.0:
        return
    health = minf(max_health, health + amount)
    health_changed.emit(health, max_health)

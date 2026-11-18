extends Control

var stick_active := false
var stick_origin := Vector2(132.0,574.0)
var stick_knob := Vector2(132.0,574.0)
var spread := 0.0
var hit_flash := 0.0

func _draw() -> void:
	if stick_active:
		draw_circle(stick_origin,76.0,Color(0.02,0.07,0.09,0.44))
		draw_arc(stick_origin,76.0,0.0,TAU,64,Color(0.28,0.82,0.82,0.46),2.0,true)
		draw_circle(stick_knob,31.0,Color(0.22,0.78,0.78,0.44))
		draw_arc(stick_knob,31.0,0.0,TAU,36,Color(0.78,0.96,0.94,0.55),1.5,true)
	var center := size*0.5
	var gap := 7.0+spread
	var length := 13.0
	var col := Color(0.88,0.96,0.93,0.86)
	if hit_flash>0.0:
		col=Color(1.0,0.76,0.28,0.95)
	draw_line(center+Vector2(-gap-length,0),center+Vector2(-gap,0),col,2.0,true)
	draw_line(center+Vector2(gap,0),center+Vector2(gap+length,0),col,2.0,true)
	draw_line(center+Vector2(0,-gap-length),center+Vector2(0,-gap),col,2.0,true)
	draw_line(center+Vector2(0,gap),center+Vector2(0,gap+length),col,2.0,true)
	draw_circle(center,2.2,col)

func update_stick(active: bool,origin: Vector2,knob: Vector2) -> void:
	stick_active=active
	stick_origin=origin
	stick_knob=knob
	queue_redraw()

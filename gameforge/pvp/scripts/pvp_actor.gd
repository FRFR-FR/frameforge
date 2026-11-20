extends CharacterBody3D
class_name PVPActor

signal defeated(actor: PVPActor)
signal health_changed(actor: PVPActor, current: float, maximum: float)
signal weapon_changed(actor: PVPActor, weapon_name: String)
signal ammo_changed(actor: PVPActor, current: int, reserve: int)

const WEAPONS := [
 {"id":"Vesper9","name":"Vesper-9","damage":25.0,"rpm":390.0,"mag":16,"reload":1.25,"range":42.0,"spread":0.012,"pellets":1},
 {"id":"FluxSMG","name":"Flux SMG","damage":13.0,"rpm":900.0,"mag":34,"reload":1.55,"range":34.0,"spread":0.038,"pellets":1},
 {"id":"AegisAR","name":"Aegis AR","damage":19.0,"rpm":720.0,"mag":30,"reload":1.7,"range":58.0,"spread":0.018,"pellets":1},
 {"id":"KestrelBurst","name":"Kestrel Burst","damage":17.0,"rpm":780.0,"mag":27,"reload":1.65,"range":54.0,"spread":0.022,"pellets":1},
 {"id":"RangerDMR","name":"Ranger DMR","damage":36.0,"rpm":300.0,"mag":15,"reload":1.9,"range":78.0,"spread":0.006,"pellets":1},
 {"id":"Longbow","name":"Longbow","damage":88.0,"rpm":62.0,"mag":5,"reload":2.45,"range":110.0,"spread":0.002,"pellets":1},
 {"id":"Breach12","name":"Breach-12","damage":10.5,"rpm":96.0,"mag":8,"reload":2.0,"range":22.0,"spread":0.075,"pellets":8},
 {"id":"BastionLMG","name":"Bastion LMG","damage":16.0,"rpm":660.0,"mag":62,"reload":2.7,"range":62.0,"spread":0.032,"pellets":1},
 {"id":"PulseCarbine","name":"Pulse Carbine","damage":22.0,"rpm":510.0,"mag":26,"reload":1.7,"range":66.0,"spread":0.014,"pellets":1},
 {"id":"ArcLance","name":"Arc Lance","damage":70.0,"rpm":145.0,"mag":6,"reload":2.25,"range":86.0,"spread":0.004,"pellets":1}
]
@export var is_player := false
@export var character_id := "Aster"
var game_root: Node
var move_input := Vector2.ZERO
var ai_direction := Vector3.ZERO
var sprint_held := false
var crouch_held := false
var jump_requested := false
var roll_seconds := 0.0
var roll_cooldown := 0.0
var roll_direction := Vector3.ZERO
var roll_restore_crouch := false
var fire_animation_seconds := 0.0
var jump_animation_seconds := 0.0
var emote_lock_seconds := 0.0
var capsule_shape: CapsuleShape3D
var collision_node: CollisionShape3D
var health := 100.0
var maximum_health := 100.0
var shield_energy := 0.0
var shield_seconds := 0.0
var shield_cooldown := 0.0
var flash_seconds := 0.0
var flash_grenades := 2
var reload_seconds := 0.0
var fire_cooldown := 0.0
var current_weapon := 2
var ammunition := 30
var reserve_ammunition := 150
var defeated_state := false
var camera_yaw := 0.0
var camera_pitch := -0.16
var camera_pivot: Node3D
var camera_arm: SpringArm3D
var camera: Camera3D
var weapon_mount: Node3D
var weapon_visual: Node3D
var character_visual: Node3D
var shield_visual: MeshInstance3D
var movement_state := ""

func _ready() -> void:
 add_to_group("pvp_fighters")
 collision_layer=1;collision_mask=1;floor_snap_length=.25
 capsule_shape=CapsuleShape3D.new();capsule_shape.radius=.37;capsule_shape.height=1.82
 collision_node=CollisionShape3D.new();collision_node.shape=capsule_shape;collision_node.position.y=.91;add_child(collision_node)
 _load_character();_create_weapon_mount();_create_shield_visual()
 if is_player:_create_camera()
 health_changed.emit(self,health,maximum_health);set_weapon(current_weapon);_play_locomotion("Idle")

func _physics_process(delta:float)->void:
 if defeated_state:return
 fire_cooldown=maxf(0.0,fire_cooldown-delta)
 shield_cooldown=maxf(0.0,shield_cooldown-delta)
 flash_seconds=maxf(0.0,flash_seconds-delta)
 roll_cooldown=maxf(0.0,roll_cooldown-delta)
 var was_rolling:=roll_seconds>0.0
 roll_seconds=maxf(0.0,roll_seconds-delta)
 if was_rolling and roll_seconds<=0.0:crouch_held=roll_restore_crouch
 fire_animation_seconds=maxf(0.0,fire_animation_seconds-delta)
 jump_animation_seconds=maxf(0.0,jump_animation_seconds-delta)
 emote_lock_seconds=maxf(0.0,emote_lock_seconds-delta)
 if shield_seconds>0.0:
  shield_seconds=maxf(0.0,shield_seconds-delta)
  if shield_seconds<=0.0 or shield_energy<=0.0:_set_shield_visible(false)
 if reload_seconds>0.0:
  reload_seconds=maxf(0.0,reload_seconds-delta)
  if reload_seconds<=0.0:_finish_reload()
 if not is_on_floor():velocity.y-=19.6*delta
 var wish:=Vector3.ZERO;var strength:=0.0
 if is_player:
  var c:=move_input.limit_length(1.0);strength=c.length();wish=Vector3(c.x,0,c.y).rotated(Vector3.UP,camera_yaw)
 else:
  strength=minf(ai_direction.length(),1.0);wish=ai_direction
 wish.y=0.0
 if wish.length()>0.001:wish=wish.normalized()
 if roll_seconds>0.0:
  wish=roll_direction
  strength=1.0
 var speed:=7.25 if sprint_held else 5.4
 if crouch_held:speed=2.65
 if not is_player:speed=5.9 if strength>.68 else 4.2
 if roll_seconds>0.0:speed=10.2
 var target:=wish*speed*strength
 var horizontal:=Vector3(velocity.x,0,velocity.z)
 horizontal=horizontal.move_toward(target,(36.0 if roll_seconds>0.0 else (30.0 if is_on_floor() else 8.0))*delta)
 if wish==Vector3.ZERO and roll_seconds<=0.0:
  horizontal=horizontal.move_toward(Vector3.ZERO,(24.0 if is_on_floor() else 2.8)*delta)
 velocity.x=horizontal.x;velocity.z=horizontal.z
 if jump_requested and is_on_floor() and not crouch_held and roll_seconds<=0.0:
  velocity.y=5.6
  jump_animation_seconds=.52
  _play_locomotion("Jump")
 jump_requested=false
 if is_player:rotation.y=camera_yaw
 elif wish.length_squared()>0.002 and roll_seconds<=0.0:
  rotation.y=lerp_angle(rotation.y,atan2(-wish.x,-wish.z),minf(1.0,13.0*delta))
 move_and_slide()
 _update_crouch_shape(delta)
 if emote_lock_seconds<=0.0:
  if roll_seconds>0.0:
   _play_locomotion("Roll")
  elif jump_animation_seconds>0.0 or fire_animation_seconds>0.0:
   pass
  else:
   _update_locomotion(horizontal.length())

func _load_character()->void:
 var path:="res://assets/characters/%s.glb"%character_id
 if not ResourceLoader.exists(path):push_error("Missing operator: "+path);return
 var packed:=load(path) as PackedScene
 if packed==null:push_error("Invalid operator GLB: "+path);return
 character_visual=packed.instantiate();character_visual.name="RiggedOperator_"+character_id;character_visual.scale=Vector3.ONE*.88;add_child(character_visual)

func _create_camera()->void:
 camera_pivot=Node3D.new();camera_pivot.position=Vector3(0,1.43,0);add_child(camera_pivot)
 camera_arm=SpringArm3D.new();camera_arm.spring_length=5.0;camera_arm.margin=.18;camera_arm.rotation.x=camera_pitch;camera_pivot.add_child(camera_arm)
 camera=Camera3D.new();camera.current=true;camera.fov=76.0;camera_arm.add_child(camera)

func apply_look_delta(delta:Vector2)->void:
 var sensitivity:=float(game_root.look_sensitivity) if game_root else 1.0
 var invert:=bool(game_root.invert_look_y) if game_root else false
 camera_yaw-=delta.x*.0038*sensitivity;camera_pitch+=delta.y*.0028*sensitivity*(-1.0 if invert else 1.0);camera_pitch=clampf(camera_pitch,-.84,.38)
 if camera_pivot:camera_pivot.rotation.y=camera_yaw;camera_arm.rotation.x=camera_pitch

func get_aim_point(distance:float=125.0)->Vector3:
 if camera:return camera.global_position+(-camera.global_basis.z)*distance
 return global_position+Vector3.UP*1.4+Vector3.FORWARD*distance

func set_move_input(v:Vector2)->void:move_input=v.limit_length(1.0)
func set_ai_direction(v:Vector3)->void:ai_direction=v.limit_length(1.0)
func set_sprint(v:bool)->void:sprint_held=v
func set_crouch(v:bool)->void:
 crouch_held=v
 if roll_seconds>0.0:roll_restore_crouch=v
func request_jump()->void:
 jump_requested=true
func request_roll()->bool:
 if defeated_state or roll_cooldown>0.0 or not is_on_floor() or roll_seconds>0.0:return false
 var direction:=Vector3.ZERO
 if is_player:
  var c:=move_input.limit_length(1.0)
  direction=Vector3(c.x,0.0,c.y).rotated(Vector3.UP,camera_yaw)
 else:
  direction=ai_direction
 if direction.length()<0.12:
  direction=-global_basis.z
 roll_direction=direction.normalized()
 roll_restore_crouch=crouch_held
 roll_seconds=0.64
 roll_cooldown=1.45
 crouch_held=true
 _play_locomotion("Roll")
 return true
func _update_crouch_shape(delta:float)->void:
 if not is_instance_valid(capsule_shape) or not is_instance_valid(collision_node):return
 var target_height:=0.96 if crouch_held or roll_seconds>0.0 else 1.82
 capsule_shape.height=move_toward(capsule_shape.height,target_height,4.8*delta)
 collision_node.position.y=capsule_shape.height*0.5
 if is_instance_valid(camera_pivot):
  camera_pivot.position.y=1.43 if target_height>1.0 else 0.95
 if is_instance_valid(character_visual):
  var target_scale_y:=0.88 if target_height>1.0 else 0.57
  character_visual.scale.y=move_toward(character_visual.scale.y,target_scale_y,3.8*delta)

func _create_weapon_mount()->void:
 weapon_mount=Node3D.new();weapon_mount.position=Vector3(.37,.68,-.25);weapon_mount.rotation.y=PI*.5;add_child(weapon_mount)

func set_weapon(index:int)->void:
 current_weapon=posmod(index,WEAPONS.size());var w:Dictionary=WEAPONS[current_weapon];ammunition=int(w["mag"]);reserve_ammunition=int(w["mag"])*5;reload_seconds=0
 if is_instance_valid(weapon_visual):weapon_visual.queue_free()
 var path:="res://assets/weapons/%s.glb"%w["id"]
 if ResourceLoader.exists(path):
  var packed:=load(path) as PackedScene
  if packed:weapon_visual=packed.instantiate();weapon_visual.scale=Vector3.ONE*.52;weapon_mount.add_child(weapon_visual)
 weapon_changed.emit(self,str(w["name"]));ammo_changed.emit(self,ammunition,reserve_ammunition)

func cycle_weapon(step:int=1)->void:set_weapon(current_weapon+step)
func reload_weapon()->void:
 if defeated_state or reload_seconds>0:return
 var mag:=int(WEAPONS[current_weapon]["mag"])
 if ammunition<mag and reserve_ammunition>0:reload_seconds=float(WEAPONS[current_weapon]["reload"]);_play_locomotion("Reload")
func _finish_reload()->void:
 var mag:=int(WEAPONS[current_weapon]["mag"]);var n:=mini(mag-ammunition,reserve_ammunition);ammunition+=n;reserve_ammunition-=n;ammo_changed.emit(self,ammunition,reserve_ammunition)

func fire_at_position(target_point:Vector3)->bool:
 if defeated_state or fire_cooldown>0 or reload_seconds>0:return false
 if ammunition<=0:reload_weapon();return false
 var w:Dictionary=WEAPONS[current_weapon];ammunition-=1;ammo_changed.emit(self,ammunition,reserve_ammunition);fire_cooldown=60.0/float(w["rpm"])
 fire_animation_seconds=0.11
 _play_locomotion("Fire")
 var origin:=global_position+Vector3.UP*1.47;var direction:=(target_point-origin).normalized();var space:=get_world_3d().direct_space_state
 for i in range(int(w["pellets"])):
  var noisy:=(direction+global_basis.x*randf_range(-float(w["spread"]),float(w["spread"]))+Vector3.UP*randf_range(-float(w["spread"]),float(w["spread"]))).normalized()
  var q:=PhysicsRayQueryParameters3D.create(origin,origin+noisy*float(w["range"]));q.exclude=[get_rid()];q.collision_mask=1
  var hit:=space.intersect_ray(q)
  if not hit.is_empty() and hit.get("collider") is PVPActor:(hit.get("collider") as PVPActor).receive_damage(float(w["damage"]),global_position)
 if game_root and game_root.has_method("show_shot_effect"):game_root.show_shot_effect(origin,origin+direction*minf(26.0,float(w["range"])))
 return true

func receive_damage(amount:float,_attacker:Vector3)->void:
 if defeated_state:return
 var remaining:=amount
 if shield_seconds>0.0 and shield_energy>0.0:
  var absorbed:=minf(shield_energy,remaining);shield_energy-=absorbed;remaining-=absorbed
 if remaining>0.0:health=maxf(0.0,health-remaining)
 if shield_energy<=0.0:_set_shield_visible(false)
 health_changed.emit(self,health,maximum_health)
 if health<=0.0:defeated_state=true;defeated.emit(self)

func activate_cyber_shield()->bool:
 if defeated_state or shield_cooldown>0.0 or shield_seconds>0.0:return false
 shield_energy=110.0;shield_seconds=5.0;shield_cooldown=13.0;_set_shield_visible(true);return true

func _create_shield_visual()->void:
 shield_visual=MeshInstance3D.new();var s:=SphereMesh.new();s.radius=1.03;s.height=2.06;shield_visual.mesh=s;shield_visual.position.y=.95
 var m:=StandardMaterial3D.new();m.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA;m.albedo_color=Color(.12,.72,1,.22);m.emission_enabled=true;m.emission=Color(.08,.6,1);m.emission_energy_multiplier=1.6;m.cull_mode=BaseMaterial3D.CULL_DISABLED;shield_visual.material_override=m;shield_visual.visible=false;add_child(shield_visual)
func _set_shield_visible(v:bool)->void:
 if is_instance_valid(shield_visual):shield_visual.visible=v

func throw_flash_grenade(target:Vector3)->bool:
 if defeated_state or flash_grenades<=0 or not game_root or not game_root.has_method("throw_flash_grenade"):return false
 flash_grenades-=1;game_root.throw_flash_grenade(self,target);return true
func apply_flash(duration:float)->void:
 flash_seconds=maxf(flash_seconds,duration)
 if is_player and game_root and game_root.has_method("show_flash_overlay"):game_root.show_flash_overlay(duration)

func play_emote(keyword:String)->bool:
 if not character_visual:return false
 for n in character_visual.find_children("*","AnimationPlayer",true,false):
  var p:=n as AnimationPlayer
  for a in p.get_animation_list():
   if keyword.to_lower() in a.to_lower():
    p.play(a,0.12)
    emote_lock_seconds=maxf(0.35,p.get_animation(a).length)
    movement_state="EMOTE"
    return true
 return false

func _play_locomotion(state:String)->void:
 if not character_visual or state==movement_state or emote_lock_seconds>0.0:return
 for n in character_visual.find_children("*","AnimationPlayer",true,false):
  var p:=n as AnimationPlayer
  for a in p.get_animation_list():
   if state.to_lower() in a.to_lower():p.play(a);movement_state=state;return
 movement_state=state
func _update_locomotion(speed:float)->void:
 if reload_seconds>0.0 or emote_lock_seconds>0.0:return
 if speed<.18:_play_locomotion("Idle")
 elif crouch_held:_play_locomotion("Crouch")
 elif sprint_held or speed>6.1:_play_locomotion("Sprint")
 else:_play_locomotion("Walk")

func reset_for_rematch(spawn:Vector3)->void:
 position=spawn;velocity=Vector3.ZERO;health=maximum_health;shield_energy=0.0;shield_seconds=0.0;shield_cooldown=0.0;flash_seconds=0.0;flash_grenades=2;defeated_state=false;roll_seconds=0.0;roll_cooldown=0.0;crouch_held=false;roll_restore_crouch=false;emote_lock_seconds=0.0;jump_animation_seconds=0.0;fire_animation_seconds=0.0
 _update_crouch_shape(1.0)
 set_weapon(current_weapon);health_changed.emit(self,health,maximum_health)

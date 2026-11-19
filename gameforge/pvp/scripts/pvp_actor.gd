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
	{"id":"PulseCarbine","name":"Pulse Carbine","damage":22.0,"rpm":510.0,

shader_type spatial;
render_mode specular_disabled;

// Sol des cartes : herbe de base et quatre couches peintes par une carte de mélange
// (splat) RVBA couvrant tout le terrain. Textures répétées en coordonnées monde
// (densité constante). Transitions « peintes » : la luminosité de chaque texture
// découpe le bord de la couche (pas de fondu flou). Teinte du décor : désaturation
// et verts plus bleus que ceux des plantes jouables (lisibilité des unités).

// R = herbe sèche, G = chemin de terre, B = herbe morte, A = sol corrompu.
uniform sampler2D splat_map : hint_default_black, filter_linear, repeat_disable;
uniform sampler2D grass_texture : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D dry_texture : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D path_texture : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D dead_texture : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D corrupted_texture : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
// Bruit lent (raccordable) : variation de luminosité et alternance de deux lectures
// tournées de l'herbe, pour casser la répétition.
uniform sampler2D macro_noise : filter_linear, repeat_enable;
uniform float macro_meters = 48.0;

// Zone couverte par la carte de mélange (m, plan XZ).
uniform vec2 map_origin = vec2(-150.0, -150.0);
uniform vec2 map_size = vec2(300.0, 300.0);
// Taille d'une répétition des textures (m).
uniform float tile_meters = 6.0;
// Netteté des bords de couche (petit = net).
uniform float edge_softness : hint_range(0.01, 0.5) = 0.08;
// Variation de luminosité à grande échelle.
uniform float macro_strength : hint_range(0.0, 0.5) = 0.1;
// Le sol corrompu est très saturé : ramené vers le reste du décor.
uniform float corrupted_saturation : hint_range(0.0, 1.0) = 0.35;
uniform float saturation : hint_range(0.0, 1.5) = 0.88;
uniform vec3 tint : source_color = vec3(0.92, 0.97, 1.0);

varying vec2 world_xz;

void vertex() {
	world_xz = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xz;
}

float luma(vec3 c) {
	return dot(c, vec3(0.299, 0.587, 0.114));
}

// Pose une couche : le poids est décalé par la luminosité de la texture vers le
// milieu de la transition, pour des bords irréguliers et francs.
vec3 layer(vec3 below, vec3 top, float weight) {
	float edge = weight + (luma(top) - 0.5) * 1.6 * weight * (1.0 - weight);
	return mix(below, top, smoothstep(0.5 - edge_softness, 0.5 + edge_softness, edge));
}

// Deux lectures (l'une tournée et décalée), choisies par le bruit lent avec un bord net.
vec3 varied(sampler2D tex, vec2 uv, float macro) {
	vec3 a = texture(tex, uv).rgb;
	vec3 b = texture(tex, mat2(vec2(0.6, -0.8), vec2(0.8, 0.6)) * uv * 0.87 + vec2(0.37, 0.11)).rgb;
	return mix(a, b, smoothstep(0.45, 0.55, macro));
}

void fragment() {
	vec2 uv = world_xz / tile_meters;
	vec4 weights = texture(splat_map, (world_xz - map_origin) / map_size);
	float macro = texture(macro_noise, world_xz / macro_meters).r;
	vec3 color = varied(grass_texture, uv, macro);
	color = layer(color, varied(dry_texture, uv, 1.0 - macro), weights.r);
	color = layer(color, varied(dead_texture, uv, macro), weights.b);
	vec3 corrupted = texture(corrupted_texture, uv * 0.8).rgb;
	corrupted = mix(vec3(luma(corrupted)), corrupted, corrupted_saturation);
	color = layer(color, corrupted, weights.a);
	color = layer(color, texture(path_texture, uv * 1.25).rgb, weights.g);
	color *= 1.0 + (texture(macro_noise, world_xz / (macro_meters * 0.37)).r - 0.5) * 2.0 * macro_strength;
	color = mix(vec3(luma(color)), color, saturation) * tint;
	ALBEDO = color;
	ROUGHNESS = 1.0;
}

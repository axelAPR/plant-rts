shader_type sky;

// Ciel cartoon : dégradé franc (bleu soutenu au zénith, clair à l'horizon), soleil
// à halo doux et nuages en aplats (blanc éclairé, bleu-gris à l'ombre) projetés sur
// un plafond. Statique (pas de TIME) : l'éclairage ambiant tiré du ciel n'est
// recalculé qu'au chargement.

uniform vec3 zenith_color : source_color = vec3(0.13, 0.45, 0.86);
uniform vec3 horizon_color : source_color = vec3(0.66, 0.87, 0.98);
uniform vec3 ground_color : source_color = vec3(0.36, 0.45, 0.33);
// Hauteur (sinus de l'élévation) où le dégradé atteint le zénith.
uniform float gradient_height : hint_range(0.05, 1.0) = 0.55;

uniform vec3 sun_color : source_color = vec3(1.0, 0.96, 0.8);
uniform float sun_size : hint_range(0.001, 0.2) = 0.035;
uniform float sun_halo : hint_range(0.0, 1.0) = 0.35;

uniform sampler2D cloud_noise : filter_linear_mipmap, repeat_enable;
uniform vec3 cloud_light : source_color = vec3(1.0, 1.0, 1.0);
uniform vec3 cloud_shadow : source_color = vec3(0.7, 0.8, 0.93);
// Part du ciel couverte (0 = aucun nuage, 1 = couvert).
uniform float cloud_coverage : hint_range(0.0, 1.0) = 0.48;
uniform float cloud_scale = 0.18;
uniform float cloud_edge : hint_range(0.001, 0.2) = 0.02;
// Décalage de lecture vers le soleil pour l'ombrage (épaisseur apparente).
uniform float cloud_shading_offset = 0.05;

void sky() {
	float up = EYEDIR.y;
	vec3 color;
	if (up >= 0.0) {
		float t = smoothstep(0.0, gradient_height, up);
		color = mix(horizon_color, zenith_color, t * t * (2.0 - t));
	} else {
		color = mix(horizon_color, ground_color, smoothstep(0.0, 0.08, -up));
	}

	if (!AT_CUBEMAP_PASS && LIGHT0_ENABLED) {
		float d = dot(EYEDIR, LIGHT0_DIRECTION);
		float disc = smoothstep(cos(sun_size), cos(sun_size * 0.8), d);
		float halo = pow(max(d, 0.0), 64.0) * sun_halo;
		color = mix(color, sun_color, clamp(disc + halo, 0.0, 1.0));
	}

	if (up > 0.0) {
		// Plafond nuageux : projection plane, compressée vers l'horizon.
		vec2 p = EYEDIR.xz / (up + 0.12) * cloud_scale;
		float n = texture(cloud_noise, p).r;
		float threshold = 1.0 - cloud_coverage;
		float mask = smoothstep(threshold, threshold + cloud_edge, n);
		vec2 to_sun = LIGHT0_ENABLED ? normalize(LIGHT0_DIRECTION.xz + vec2(1e-4)) : vec2(0.0, 1.0);
		float n_sun = texture(cloud_noise, p + to_sun * cloud_shading_offset).r;
		float lit = step(n, n_sun + 0.015);
		vec3 cloud = mix(cloud_shadow, cloud_light, lit);
		// Les nuages s'effacent près de l'horizon (pas de bande dense).
		mask *= smoothstep(0.02, 0.18, up);
		color = mix(color, cloud, mask);
	}
	COLOR = color;
}

let defaultLang = 'en';

let dicts = {
	'en': {
		'success_text': 'Your answers have been successfully registered',
		'thankyou_text': 'Thank you!',
		'welcome_text': 'Welcome!',
		'photo_consent_text': 'I authorize the transfer\
			 of my image rights for the publication of photographs',
                'email_consent_text': 'I authorize to receive \
			communications from the organizers of the event and/or the venue by email',
                'submit_text': 'Confirm attendance'
	},
	'es': {
		'success_text': 'Tus respuestas se han registrado correctamente',
		'thankyou_text': '¡Gracias!',
		'welcome_text': '¡Te damos la bienvenida!',
		'photo_consent_text': 'Autorizo la cesión de mis \
			derechos de imagen para la publicación de fotografías',
		'email_consent_text': 'Autorizo recibir comunicaciones \
			de los organizadores del evento y/o de la sede por email',
		'submit_text': 'Confirmar asistencia'
	}
}

function resolveLanguageFromLocale(locale) {
	if(locale.startsWith('es')) {
		return 'es';
	}
	return 'en';
}

function translateText() {
	let locale = Intl.DateTimeFormat().resolvedOptions().locale;
	let language = resolveLanguageFromLocale(locale);
	let translation = dicts[language];
	let strings = Object.keys(translation);
	for(let key of strings) {
		let value = translation[key];
		let element = document.getElementById(key);
		if(element) {
			if(element.innerHTML) {
				element.innerHTML = value;
			}
			else if(element.value) {
				element.value = value;
			}
		}
	}
}

translateText();

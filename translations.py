"""
translations.py  –  LEAP Lawrence Bilingual Support
Supports: English (en) and Dominican Spanish (es)
"""

TRANSLATIONS = {

    # ── Global / Header ──────────────────────────────────────────────
    "city_name": {
        "en": "City of Lawrence",
        "es": "Ciudad de Lawrence",
    },
    "program_name": {
        "en": "Lawrence Energy Affordability Project (LEAP) · Mass Save - Community First Partnership",
        "es": "Proyecto de Asequibilidad Energética de Lawrence (LEAP) · Mass Save - Community First Partnership",
    },
    "footer": {
        "en": "Energy Affordability Program · Mass Save - Community First Partnership",
        "es": "Programa de Asequibilidad de Energía · Mass Save - Community First Partnership",
    },
    "lang_toggle": {
        "en": "Español",
        "es": "English",
    },
    "demo_banner": {
        "en": "DEMO SITE",
        "es": "SITIO DE DEMOSTRACIÓN",
    },
    "footer_demo_disclaimer": {
        "en": "⚠️ DEMO ONLY — Not an official City of Lawrence site. All addresses are fictitious. Data entered is not collected or acted upon.",
        "es": "⚠️ SOLO DEMOSTRACIÓN — No es un sitio oficial de la Ciudad de Lawrence. Todas las direcciones son ficticias. Los datos ingresados no son recopilados ni procesados.",
    },

    # ── ROLES ────────────────────────────────────────────────────────
    "role_renter": {
        "en": "Renter",
        "es": "Inquilino/a",
    },
    "role_owner_occupant": {
        "en": "Owner-Occupant",
        "es": "Dueño que vive en la propiedad",
    },
    "role_landlord": {
        "en": "Landlord",
        "es": "Arrendador/a",
    },
    "role_property_manager": {
        "en": "Property Manager",
        "es": "Administrador/a de propiedad",
    },
    "role_small_business": {
        "en": "Small Business",
        "es": "Pequeño negocio",
    },

    # ── INTENTS ──────────────────────────────────────────────────────
    "intent_enroll": {
        "en": "I want to enroll in Mass Save now",
        "es": "Quiero inscribirme en Mass Save ahora",
    },
    "intent_event": {
        "en": "I want to attend a City information event",
        "es": "Quiero asistir a un evento informativo de la Ciudad",
    },
    "intent_assistance": {
        "en": "I need help understanding the program",
        "es": "Necesito ayuda para entender el programa",
    },
    "intent_enrolled_update": {
        "en": "I already enrolled with Mass Save",
        "es": "Ya me inscribí con Mass Save",
    },
    "intent_done": {
        "en": "I'm all set for now",
        "es": "Por ahora estoy bien",
    },

    # ── index.html ───────────────────────────────────────────────────
    "index_title": {
        "en": "No-Cost Energy Upgrades for Lawrence Residents",
        "es": "Mejoras de Energía Sin Costo para Residentes de Lawrence",
    },
    "index_subtitle": {
        "en": "The City of Lawrence is partnering with Mass Save to bring no-cost energy efficiency upgrades to renters and landlords. Find out if your property qualifies — it takes less than two minutes.",
        "es": "La Ciudad de Lawrence se ha unido a Mass Save para ofrecer mejoras de eficiencia energética sin costo a inquilinos y arrendadores. Averigüe si su propiedad califica — toma menos de dos minutos.",
    },
    "index_qr_alert_title": {
        "en": "Did you receive a letter with a QR code?",
        "es": "¿Recibió una carta con un código QR?",
    },
    "index_qr_alert_body": {
        "en": "Scan the QR code on your letter to get started with your property pre-identified. Or enter your UPIN below if you have it handy.",
        "es": "Escanee el código QR de su carta para comenzar con su propiedad ya identificada. O escriba su UPIN abajo si lo tiene a mano.",
    },
    "index_upin_label": {
        "en": "Enter Your UPIN",
        "es": "Ingrese su UPIN",
    },
    "index_upin_hint": {
        "en": "(from your letter)",
        "es": "(de su carta)",
    },
    "index_upin_placeholder": {
        "en": "e.g. ABCD123XYZ",
        "es": "ej. ABCD123XYZ",
    },
    "index_go_btn": {
        "en": "Go →",
        "es": "Ir →",
    },
    "index_or": {
        "en": "or",
        "es": "o",
    },
    "index_no_letter": {
        "en": "No letter? No problem — look up your property by address:",
        "es": "¿No tiene carta? No hay problema — busque su propiedad por dirección:",
    },
    "index_find_address_btn": {
        "en": "Find My Address →",
        "es": "Buscar Mi Dirección →",
    },
    "index_address_hint": {
        "en": "We'll ask a quick question first to look up the right records for you.",
        "es": "Le haremos una pregunta rápida primero para buscar los registros correctos.",
    },
    "index_privacy_title": {
        "en": "Your privacy matters.",
        "es": "Su privacidad es importante.",
    },
    "index_privacy_body": {
        "en": "The City uses your address only to connect you with benefits you have already paid for through your utility bills. Registration with the City is optional. Official enrollment occurs at",
        "es": "La Ciudad usa su dirección únicamente para conectarle con beneficios que ya pagó a través de sus facturas de servicios. El registro con la Ciudad es opcional. La inscripción oficial se realiza en",
    },

    # ── start_generic.html ───────────────────────────────────────────
    "start_title": {
        "en": "Who Are You?",
        "es": "¿Quién es Usted?",
    },
    "start_subtitle": {
        "en": "Tell us your role so we can look up the right information for you.",
        "es": "Díganos su rol para que podamos buscar la información correcta para usted.",
    },
    "continue_btn": {
        "en": "Continue →",
        "es": "Continuar →",
    },
    "back_btn": {
        "en": "← Back",
        "es": "← Atrás",
    },

    # ── Step indicators ──────────────────────────────────────────────
    "step_role": {
        "en": "Role",
        "es": "Rol",
    },
    "step_street": {
        "en": "Street",
        "es": "Calle",
    },
    "step_address": {
        "en": "Address",
        "es": "Dirección",
    },
    "step_intent": {
        "en": "Intent",
        "es": "Propósito",
    },
    "step_contact": {
        "en": "Contact",
        "es": "Contacto",
    },

    # ── Error / validation messages ──────────────────────────────────
    "error_select_role": {
        "en": "Please select a role.",
        "es": "Por favor seleccione un rol.",
    },
    "error_select_option": {
        "en": "Please select an option.",
        "es": "Por favor seleccione una opción.",
    },
    "error_street_name_only": {
        "en": "Please enter the street name only — no house number. Example: Exeter",
        "es": "Por favor escriba solo el nombre de la calle — sin número de casa. Ejemplo: Exeter",
    },
    "error_street_required": {
        "en": "Please enter a street name.",
        "es": "Por favor ingrese un nombre de calle.",
    },
    "error_street_not_found": {
        "en": "We couldn't find that street in our records. Please check the spelling, or",
        "es": "No encontramos esa calle en nuestros registros. Verifique la ortografía, o",
    },
    "error_street_not_found_link": {
        "en": "let us connect you with an Energy Advocate",
        "es": "permítanos conectarle con un Asesor de Energía",
    },
    "error_valid_number": {
        "en": "Please enter a valid number.",
        "es": "Por favor ingrese un número válido.",
    },
    "error_select_address": {
        "en": "Please select your address.",
        "es": "Por favor seleccione su dirección.",
    },
    "error_enter_address": {
        "en": "Please enter your street address.",
        "es": "Por favor ingrese su dirección.",
    },
    "error_upin_missing": {
        "en": "No UPIN found. Use your QR code or <a href='/'>enter your address here</a>.",
        "es": "No se encontró UPIN. Use su código QR o <a href='/'>ingrese su dirección aquí</a>.",
    },
    "error_upin_invalid": {
        "en": "This UPIN is not valid. Please contact City Hall.",
        "es": "Este UPIN no es válido. Por favor contacte al Ayuntamiento.",
    },

    # ── Language selection (landing) ─────────────────────────────────
    "lang_select_prompt": {
        "en": "Choose your language",
        "es": "Elija su idioma",
    },

    # ── confirm_address.html ─────────────────────────────────────────
    "confirm_step_address": {
        "en": "Address",
        "es": "Dirección",
    },
    "confirm_step_role": {
        "en": "Role",
        "es": "Rol",
    },
    "confirm_step_intent": {
        "en": "Intent",
        "es": "Propósito",
    },
    "confirm_step_contact": {
        "en": "Contact",
        "es": "Contacto",
    },
    "confirm_title": {
        "en": "Is This Your Property?",
        "es": "¿Es Esta Su Propiedad?",
    },
    "confirm_subtitle": {
        "en": "Please confirm the address before we continue.",
        "es": "Por favor confirme la dirección antes de continuar.",
    },
    "confirm_heat_label": {
        "en": "Heat:",
        "es": "Calefacción:",
    },
    "confirm_units_label": {
        "en": "Units:",
        "es": "Unidades:",
    },
    "confirm_yes_btn": {
        "en": "Yes, this is my address →",
        "es": "Sí, esta es mi dirección →",
    },
    "confirm_no_btn": {
        "en": "No, search again",
        "es": "No, buscar de nuevo",
    },

    # ── contact.html ─────────────────────────────────────────────────
    "contact_title_event_rsvp": {
        "en": "You're Registered — One Last Step",
        "es": "Está Registrado/a — Un Último Paso",
    },
    "contact_subtitle_event_rsvp": {
        "en": "Your spot is saved. To let you know about any changes to the event — such as a venue update or rescheduling — please leave a phone number or email below. You can skip this if you prefer, but we won't be able to reach you if anything changes.",
        "es": "Su lugar está reservado. Para informarle sobre cualquier cambio en el evento — como cambio de lugar o reprogramación — deje un número de teléfono o correo abajo. Puede omitir esto si prefiere, pero no podremos contactarle si algo cambia.",
    },
    "contact_title_no_events": {
        "en": "We'll Let You Know",
        "es": "Le Avisaremos",
    },
    "contact_subtitle_no_events": {
        "en": "No sessions are scheduled right now, but we're actively planning the next one. Leave your contact info below and you'll be among the first to hear when a date is confirmed. You can skip this, but then we won't be able to notify you.",
        "es": "No hay sesiones programadas ahora mismo, pero estamos planificando la próxima. Deje su información de contacto y será de los primeros en saber cuando se confirme una fecha. Puede omitir esto, pero no podremos notificarle.",
    },
    "contact_title_enroll": {
        "en": "Before You Go",
        "es": "Antes de Continuar",
    },
    "contact_subtitle_enroll": {
        "en": "You're about to be connected to Mass Save to complete your enrollment. If you'd like City staff to follow up and make sure the process goes smoothly, leave your contact info below. This is optional — you can skip straight to enrollment.",
        "es": "Está a punto de ser conectado/a a Mass Save para completar su inscripción. Si desea que el personal de la Ciudad le dé seguimiento, deje su información abajo. Es opcional — puede ir directo a la inscripción.",
    },
    "contact_title_assistance": {
        "en": "We'll Follow Up With You",
        "es": "Le Daremos Seguimiento",
    },
    "contact_subtitle_assistance": {
        "en": "An Energy Advocate will reach out to walk you through your options. Please leave at least one way to contact you below so we can get in touch. You can skip this, but without contact info we won't be able to follow up.",
        "es": "Un Asesor de Energía se comunicará con usted para explicarle sus opciones. Por favor deje al menos una forma de contacto. Puede omitir esto, pero sin información de contacto no podremos darle seguimiento.",
    },
    "contact_title_generic": {
        "en": "Stay in Touch",
        "es": "Manténgase en Contacto",
    },
    "contact_optional_label": {
        "en": "(Optional)",
        "es": "(Opcional)",
    },
    "contact_subtitle_generic": {
        "en": "Leave your contact information if you'd like City staff to follow up with you about the program. This is completely optional.",
        "es": "Deje su información de contacto si desea que el personal de la Ciudad le contacte sobre el programa. Es completamente opcional.",
    },
    "contact_role_label": {
        "en": "Role:",
        "es": "Rol:",
    },
    "contact_prior_alert": {
        "en": "We've filled in your contact details from your last visit. Please update anything that has changed.",
        "es": "Hemos completado sus datos de contacto de su última visita. Por favor actualice lo que haya cambiado.",
    },
    "contact_name_label": {
        "en": "Your Name",
        "es": "Su Nombre",
    },
    "contact_name_placeholder": {
        "en": "First and last name",
        "es": "Nombre y apellido",
    },
    "contact_phone_label": {
        "en": "Phone Number",
        "es": "Número de Teléfono",
    },
    "contact_email_label": {
        "en": "Email Address",
        "es": "Correo Electrónico",
    },
    "contact_privacy_note": {
        "en": "Your contact information is used only by City staff to coordinate outreach and support. It is never shared with third parties.",
        "es": "Su información de contacto es usada únicamente por el personal de la Ciudad para coordinar comunicaciones y apoyo. Nunca se comparte con terceros.",
    },
    "contact_finish_btn": {
        "en": "Finish →",
        "es": "Finalizar →",
    },
    "contact_skip_btn": {
        "en": "Skip this step",
        "es": "Omitir este paso",
    },

    # ── done.html ────────────────────────────────────────────────────
    "done_title": {
        "en": "You're All Set!",
        "es": "¡Todo Listo!",
    },
    "done_subtitle": {
        "en": "Thank you for registering with the City of Lawrence Energy Affordability Program. A City staff member may follow up if you requested assistance.",
        "es": "Gracias por registrarse con el Programa de Asequibilidad de Energía de la Ciudad de Lawrence. Un miembro del personal de la Ciudad puede darle seguimiento si solicitó asistencia.",
    },
    "done_next_step_title": {
        "en": "Next step: Enroll with Mass Save",
        "es": "Próximo paso: Inscríbase con Mass Save",
    },
    "done_next_step_body": {
        "en": "To receive no-cost energy upgrades, you must enroll directly with Mass Save. It's free and takes about 5 minutes.",
        "es": "Para recibir mejoras de energía sin costo, debe inscribirse directamente con Mass Save. Es gratis y toma unos 5 minutos.",
    },
    "done_masssave_btn": {
        "en": "Go to masssave.com/Lawrence →",
        "es": "Ir a masssave.com/Lawrence →",
    },
    "done_questions": {
        "en": "Questions? Call the City at",
        "es": "¿Preguntas? Llame a la Ciudad al",
    },
    "done_or_visit": {
        "en": "or visit City Hall.",
        "es": "o visítenos en el Ayuntamiento.",
    },

    # ── error.html ───────────────────────────────────────────────────
    "error_title": {
        "en": "Something Went Wrong",
        "es": "Algo Salió Mal",
    },
    "error_start_over_btn": {
        "en": "← Start Over",
        "es": "← Comenzar de Nuevo",
    },
    "error_need_help": {
        "en": "Need help? Call",
        "es": "¿Necesita ayuda? Llame al",
    },
    "error_or_visit": {
        "en": "or visit City Hall.",
        "es": "o visítenos en el Ayuntamiento.",
    },

    # ── intent.html ──────────────────────────────────────────────────
    "intent_title": {
        "en": "What Would You Like to Do?",
        "es": "¿Qué Desea Hacer?",
    },
    "intent_subtitle": {
        "en": "You can enroll with Mass Save right now, learn more at a City event, or ask for help from City staff.",
        "es": "Puede inscribirse con Mass Save ahora mismo, aprender más en un evento de la Ciudad, o pedir ayuda al personal de la Ciudad.",
    },
    "intent_remember_title": {
        "en": "Remember:",
        "es": "Recuerde:",
    },
    "intent_remember_body": {
        "en": "Official enrollment happens at",
        "es": "La inscripción oficial se realiza en",
    },
    "intent_remember_suffix": {
        "en": "The City's registration is separate and optional.",
        "es": "El registro de la Ciudad es independiente y opcional.",
    },

    # ── address_not_found.html ───────────────────────────────────────
    "notfound_title": {
        "en": "We Can Help You Get Connected",
        "es": "Podemos Ayudarle a Conectarse",
    },
    "notfound_subtitle": {
        "en": "We weren't able to find your address automatically, but that doesn't mean you're not eligible — many Lawrence residents qualify for no-cost energy upgrades.",
        "es": "No pudimos encontrar su dirección automáticamente, pero eso no significa que no sea elegible — muchos residentes de Lawrence califican para mejoras de energía sin costo.",
    },
    "notfound_alert_title": {
        "en": "An Energy Advocate can help you directly.",
        "es": "Un Asesor de Energía puede ayudarle directamente.",
    },
    "notfound_alert_body": {
        "en": "Call us at",
        "es": "Llámenos al",
    },
    "notfound_alert_suffix": {
        "en": "or leave your contact information below and we'll reach out to you.",
        "es": "o deje su información de contacto abajo y nos comunicaremos con usted.",
    },
    "notfound_address_label": {
        "en": "Your Address",
        "es": "Su Dirección",
    },
    "notfound_address_hint": {
        "en": "(as best you can)",
        "es": "(lo mejor que pueda)",
    },
    "notfound_callback_btn": {
        "en": "Request a Callback →",
        "es": "Solicitar una Llamada →",
    },
    "notfound_start_over_btn": {
        "en": "← Start Over",
        "es": "← Comenzar de Nuevo",
    },

    # ── address_street.html ──────────────────────────────────────────
    "street_title": {
        "en": "What Street Do You Live On?",
        "es": "¿En Qué Calle Vive?",
    },
    "street_subtitle": {
        "en": "Enter the street name only — no house number. For example:",
        "es": "Ingrese solo el nombre de la calle — sin número de casa. Por ejemplo:",
    },
    "street_looking_up": {
        "en": "Looking up properties for:",
        "es": "Buscando propiedades para:",
    },
    "street_label": {
        "en": "Street Name",
        "es": "Nombre de la Calle",
    },
    "street_hint": {
        "en": "Street name only — do not include a house number.",
        "es": "Solo el nombre de la calle — no incluya número de casa.",
    },
    "street_search_btn": {
        "en": "Search →",
        "es": "Buscar →",
    },
    "street_multiple_found": {
        "en": "We found",
        "es": "Encontramos",
    },
    "street_matching": {
        "en": "matching",
        "es": "que coinciden con",
    },
    "street_which_one": {
        "en": "Which one is yours?",
        "es": "¿Cuál es la suya?",
    },
    "street_try_again_btn": {
        "en": "← Try again",
        "es": "← Intentar de nuevo",
    },

    # ── address_pick.html ────────────────────────────────────────────
    "pick_title": {
        "en": "Select Your Address",
        "es": "Seleccione Su Dirección",
    },
    "pick_found": {
        "en": "We found",
        "es": "Encontramos",
    },
    "pick_address_singular": {
        "en": "address",
        "es": "dirección",
    },
    "pick_address_plural": {
        "en": "addresses",
        "es": "direcciones",
    },
    "pick_on_street": {
        "en": "on",
        "es": "en",
    },
    "pick_showing_for": {
        "en": "Showing results for:",
        "es": "Mostrando resultados para:",
    },
    "pick_select_label": {
        "en": "Your Address",
        "es": "Su Dirección",
    },
    "pick_select_default": {
        "en": "— Select your address —",
        "es": "— Seleccione su dirección —",
    },
    "pick_not_listed": {
        "en": "My address isn't listed — enter it manually",
        "es": "Mi dirección no está en la lista — ingresarla manualmente",
    },
    "pick_manual_alert": {
        "en": "No problem — enter your address below and we'll still connect you with the program.",
        "es": "No hay problema — ingrese su dirección abajo y le conectaremos con el programa.",
    },
    "pick_manual_street_label": {
        "en": "Street Address",
        "es": "Dirección",
    },
    "pick_manual_unit_label": {
        "en": "Unit Number",
        "es": "Número de Unidad",
    },
    "pick_manual_unit_hint": {
        "en": "(if applicable)",
        "es": "(si aplica)",
    },
    "pick_confirm_btn": {
        "en": "This Is My Address →",
        "es": "Esta Es Mi Dirección →",
    },
    "pick_no_records_alert": {
        "en": "We don't have records for this street, but you can still register. Enter your address below and we'll connect you with the program.",
        "es": "No tenemos registros para esta calle, pero igual puede registrarse. Ingrese su dirección abajo y le conectaremos con el programa.",
    },
    "pick_try_street_btn": {
        "en": "← Try different street",
        "es": "← Intentar otra calle",
    },
    "pick_no_props_error": {
        "en": "No properties found on",
        "es": "No se encontraron propiedades en",
    },
    "pick_try_different": {
        "en": "Try a different street",
        "es": "Intentar una calle diferente",
    },
    "pick_get_help": {
        "en": "get help from an Energy Advocate",
        "es": "obtener ayuda de un Asesor de Energía",
    },

    # ── Shared step labels (landlord flow) ───────────────────────────
    "step_property": {
        "en": "Property",
        "es": "Propiedad",
    },

    # ── welcome_back.html ────────────────────────────────────────────
    "welcome_back_title": {
        "en": "Welcome Back!",
        "es": "¡Bienvenido/a de Nuevo!",
    },
    "welcome_back_subtitle": {
        "en": "We recognize your property at",
        "es": "Reconocemos su propiedad en",
    },
    "welcome_back_subtitle2": {
        "en": "Let's make this quick.",
        "es": "Hagamos esto rápido.",
    },
    "welcome_back_last_visit_prompt": {
        "en": "Last time you visited as",
        "es": "La última vez visitó como",
    },
    "welcome_back_still_correct": {
        "en": "Is that still correct?",
        "es": "¿Sigue siendo correcto?",
    },
    "welcome_back_registered": {
        "en": "a registered visitor",
        "es": "un visitante registrado",
    },
    "welcome_back_last_visit_badge": {
        "en": "Last visit",
        "es": "Última visita",
    },
    "welcome_back_role_locked": {
        "en": "Your role is confirmed from your registration code.",
        "es": "Su rol está confirmado por su código de registro.",
    },

    # ── returning_action.html ────────────────────────────────────────
    "returning_title": {
        "en": "What Brings You Back?",
        "es": "¿Qué le Trae de Vuelta?",
    },
    "returning_subtitle_events": {
        "en": "You can RSVP to an upcoming session and choose a next step — both are independent.",
        "es": "Puede reservar su lugar en una próxima sesión y elegir un próximo paso — ambos son independientes.",
    },
    "returning_subtitle_no_events": {
        "en": "Let us know what you need and we'll make sure the right person follows up.",
        "es": "Díganos qué necesita y nos aseguraremos de que la persona correcta le dé seguimiento.",
    },
    "returning_rsvp_prompt": {
        "en": "RSVP to an upcoming session:",
        "es": "Reserve su lugar en una próxima sesión:",
    },
    "returning_no_event_option": {
        "en": "No event RSVP this visit",
        "es": "Sin reserva de evento esta visita",
    },
    "returning_action_prompt": {
        "en": "What else would you like to do?",
        "es": "¿Qué más desea hacer?",
    },
    "returning_action_assistance_title": {
        "en": "Please contact me — I need help with the program",
        "es": "Por favor contácteme — necesito ayuda con el programa",
    },
    "returning_action_assistance_body": {
        "en": "An Energy Advocate will reach out to walk you through your options.",
        "es": "Un Asesor de Energía se comunicará con usted para explicarle sus opciones.",
    },
    "returning_action_assistance_no_events": {
        "en": "We'll also let you know as soon as the next session is scheduled.",
        "es": "También le avisaremos tan pronto se programe la próxima sesión.",
    },
    "returning_action_enroll_title": {
        "en": "I'm ready to enroll with Mass Save now",
        "es": "Estoy listo/a para inscribirme con Mass Save ahora",
    },
    "returning_action_enroll_body": {
        "en": "We'll take you directly to the Mass Save enrollment page.",
        "es": "Le llevaremos directamente a la página de inscripción de Mass Save.",
    },
    "returning_action_enrolled_title": {
        "en": "I already enrolled with Mass Save — update my record",
        "es": "Ya me inscribí con Mass Save — actualizar mi registro",
    },
    "returning_action_enrolled_body": {
        "en": "Let us know so we can track program progress for your property.",
        "es": "Háganos saber para que podamos dar seguimiento al progreso del programa en su propiedad.",
    },
    "returning_action_other": {
        "en": "Something else",
        "es": "Algo más",
    },

    # ── landlord_units.html ──────────────────────────────────────────
    "lunits_title": {
        "en": "How Many Rental Units Are in This Property?",
        "es": "¿Cuántas Unidades de Alquiler Tiene Esta Propiedad?",
    },
    "lunits_subtitle": {
        "en": "Please enter the total number of rental units at this address, including any units you occupy yourself.",
        "es": "Por favor ingrese el número total de unidades de alquiler en esta dirección, incluyendo cualquier unidad que usted mismo ocupe.",
    },
    "lunits_label": {
        "en": "Number of Rental Units",
        "es": "Número de Unidades de Alquiler",
    },

    # ── landlord_units_confirm.html ──────────────────────────────────
    "lunits_confirm_title": {
        "en": "Can You Help Us Confirm?",
        "es": "¿Puede Ayudarnos a Confirmar?",
    },
    "lunits_confirm_subtitle_a": {
        "en": "Our records show",
        "es": "Nuestros registros muestran",
    },
    "lunits_confirm_unit_s": {
        "en": "unit(s)",
        "es": "unidad(es)",
    },
    "lunits_confirm_subtitle_b": {
        "en": "at this address, but you entered",
        "es": "en esta dirección, pero usted ingresó",
    },
    "lunits_confirm_subtitle_c": {
        "en": "That's quite a difference — can you confirm your count is correct?",
        "es": "Hay una diferencia notable — ¿puede confirmar que su conteo es correcto?",
    },
    "lunits_confirm_alert": {
        "en": "This doesn't affect your eligibility. We just want to make sure our records are up to date so we can plan our outreach correctly.",
        "es": "Esto no afecta su elegibilidad. Solo queremos asegurarnos de que nuestros registros estén actualizados para planificar nuestra comunicación correctamente.",
    },
    "lunits_confirm_yes": {
        "en": "Yes, I have",
        "es": "Sí, tengo",
    },
    "lunits_confirm_yes_suffix": {
        "en": "units — please update your records",
        "es": "unidades — por favor actualice sus registros",
    },
    "lunits_confirm_no": {
        "en": "I may have made a mistake — use your records for now",
        "es": "Es posible que me haya equivocado — use sus registros por ahora",
    },

    # ── landlord_repeat.html ─────────────────────────────────────────
    "lrepeat_title": {
        "en": "Welcome Back!",
        "es": "¡Bienvenido/a de Nuevo!",
    },
    "lrepeat_subtitle": {
        "en": "We see you've visited before for",
        "es": "Vemos que ha visitado antes para",
    },
    "lrepeat_subtitle2": {
        "en": "A couple of quick questions to help us serve you better.",
        "es": "Un par de preguntas rápidas para servirle mejor.",
    },
    "lrepeat_enrolled_prompt": {
        "en": "Have you already enrolled with Mass Save?",
        "es": "¿Ya se ha inscrito con Mass Save?",
    },
    "lrepeat_enrolled_yes": {
        "en": "Yes, I've enrolled",
        "es": "Sí, ya me inscribí",
    },
    "lrepeat_enrolled_no": {
        "en": "Not yet",
        "es": "Todavía no",
    },
    "lrepeat_callback_prompt": {
        "en": "Would you like a call back from City staff?",
        "es": "¿Le gustaría recibir una llamada del personal de la Ciudad?",
    },
    "lrepeat_callback_yes": {
        "en": "Yes, please call me",
        "es": "Sí, por favor llámeme",
    },
    "lrepeat_callback_no": {
        "en": "No thanks",
        "es": "No, gracias",
    },

    # ── landlord_events.html ─────────────────────────────────────────
    "levents_title": {
        "en": "You're Almost Done",
        "es": "Ya Casi Termina",
    },
    "levents_subtitle": {
        "en": "Let us know if you'd like to attend an upcoming session and what you'd like to do next. You can choose both.",
        "es": "Díganos si desea asistir a una próxima sesión y qué le gustaría hacer después. Puede elegir ambas opciones.",
    },
    "levents_section_a_prompt": {
        "en": "Would you like to attend an upcoming City information session?",
        "es": "¿Le gustaría asistir a una próxima sesión informativa de la Ciudad?",
    },
    "levents_no_event_option": {
        "en": "No thanks, skip the events",
        "es": "No, gracias, omitir los eventos",
    },
    "levents_no_events_alert": {
        "en": "No sessions are currently scheduled. Check back soon — we add new sessions regularly. You can still enroll directly with Mass Save or request a callback below.",
        "es": "No hay sesiones programadas actualmente. Vuelva pronto — agregamos nuevas sesiones regularmente. Puede inscribirse directamente con Mass Save o solicitar una llamada abajo.",
    },
    "levents_section_b_prompt": {
        "en": "What would you like to do next?",
        "es": "¿Qué le gustaría hacer a continuación?",
    },
    "levents_enroll_title": {
        "en": "Enroll with Mass Save now",
        "es": "Inscribirse con Mass Save ahora",
    },
    "levents_enroll_body": {
        "en": "We'll take you directly to the Mass Save enrollment page.",
        "es": "Le llevaremos directamente a la página de inscripción de Mass Save.",
    },
    "levents_callback_title": {
        "en": "Please contact me — I need help understanding the program",
        "es": "Por favor contácteme — necesito ayuda para entender el programa",
    },
    "levents_callback_body": {
        "en": "An Energy Advocate will reach out to walk you through your options.",
        "es": "Un Asesor de Energía se comunicará con usted para explicarle sus opciones.",
    },
    "levents_done_option": {
        "en": "I'm all set for now",
        "es": "Por ahora estoy bien",
    },

    # ── Shared event display strings ─────────────────────────────────
    "event_spots_remaining": {
        "en": "spots remaining",
        "es": "lugares disponibles",
    },
    "event_spot_remaining": {
        "en": "spot remaining",
        "es": "lugar disponible",
    },
    "event_wards_label": {
        "en": "Ward",
        "es": "Distrito",
    },
    "event_wards_label_plural": {
        "en": "Wards",
        "es": "Distritos",
    },
    "event_already_registered": {
        "en": "You're already registered for this event",
        "es": "Ya está registrado/a para este evento",
    },
    "event_already_registered_note": {
        "en": "Selecting this again will not create a duplicate registration.",
        "es": "Seleccionar esto nuevamente no creará un registro duplicado.",
    },

    # ── event_select.html ────────────────────────────────────────────
    "eselect_title": {
        "en": "Upcoming Information Sessions",
        "es": "Próximas Sesiones Informativas",
    },
    "eselect_subtitle": {
        "en": "Select a session you'd like to attend. We'll save your spot and City staff will follow up with details.",
        "es": "Seleccione una sesión a la que desea asistir. Guardaremos su lugar y el personal de la Ciudad le enviará los detalles.",
    },
    "eselect_step_event": {
        "en": "Event",
        "es": "Evento",
    },
    "eselect_none_option": {
        "en": "None of these work for me — notify me about future sessions",
        "es": "Ninguna me funciona — notifíqueme sobre futuras sesiones",
    },
    "eselect_no_events_title": {
        "en": "No sessions scheduled yet.",
        "es": "Aún no hay sesiones programadas.",
    },
    "eselect_no_events_body": {
        "en": "We're actively planning the next sessions. Leave your contact info on the next page and we'll notify you as soon as one is confirmed.",
        "es": "Estamos planificando activamente las próximas sesiones. Deje su información de contacto en la siguiente página y le avisaremos en cuanto se confirme una.",
    },
    "levents_enrolled_subtitle": {
        "en": "Great — you're already enrolled with Mass Save! Would you like to attend an upcoming session to learn more about what to expect?",
        "es": "¡Excelente — ya está inscrito/a con Mass Save! ¿Le gustaría asistir a una próxima sesión para aprender más sobre qué esperar?",
    },
    "levents_enrolled_no_event_option": {
        "en": "No thanks — cancel my reservation",
        "es": "No, gracias — cancelar mi reservación",
    },
    "levents_returning_title": {
        "en": "Welcome Back — What Would You Like to Do?",
        "es": "Bienvenido/a de Nuevo — ¿Qué Desea Hacer?",
    },
    "levents_returning_subtitle": {
        "en": "Would you like to attend an upcoming City information session?",
        "es": "¿Le gustaría asistir a una próxima sesión informativa de la Ciudad?",
    },
    "seal_confirm_msg": {
        "en": "Return to the home page? Your progress will be lost.",
        "es": "¿Volver a la página de inicio? Se perderá su progreso.",
    },
    "done_rsvp_section_title": {
        "en": "Your Event Registration",
        "es": "Su Registro de Evento",
    },
    "done_rsvp_cancel_btn": {
        "en": "Cancel Registration",
        "es": "Cancelar Registro",
    },
    "done_rsvp_cancel_confirm": {
        "en": "Cancel your registration for this event?",
        "es": "¿Cancelar su registro para este evento?",
    },
    # ── renter_login.html ────────────────────────────────────────────
    "renter_login_heading": {
        "en": "Renter Sign-In",
        "es": "Acceso para Inquilinos",
    },
    "renter_login_subtext": {
        "en": "Enter the UPIN from your letter or QR code to get started.",
        "es": "Ingrese el UPIN de su carta o código QR para comenzar.",
    },
    "renter_login_upin_label": {
        "en": "Your UPIN",
        "es": "Su UPIN",
    },
    "renter_login_submit": {
        "en": "Sign In →",
        "es": "Ingresar →",
    },
    "renter_login_no_upin_text": {
        "en": "Don't have a UPIN?",
        "es": "¿No tiene un UPIN?",
    },
    "renter_login_no_upin_link": {
        "en": "Find your address here",
        "es": "Busque su dirección aquí",
    },
}


def t(key, lang="en"):
    """Return translated string for key in given language. Falls back to English."""
    entry = TRANSLATIONS.get(key, {})
    return entry.get(lang) or entry.get("en") or key


def get_roles(lang="en"):
    """Return ROLES list in the given language."""
    return [
        ("renter",           t("role_renter",           lang)),
        ("owner_occupant",   t("role_owner_occupant",   lang)),
        ("landlord",         t("role_landlord",         lang)),
        ("property_manager", t("role_property_manager", lang)),
        ("small_business",   t("role_small_business",   lang)),
    ]


def get_intents(lang="en"):
    """Return INTENTS list in the given language."""
    return [
        ("enroll",          t("intent_enroll",          lang)),
        ("event",           t("intent_event",           lang)),
        ("assistance",      t("intent_assistance",      lang)),
        ("enrolled_update", t("intent_enrolled_update", lang)),
        ("done",            t("intent_done",            lang)),
    ]


def get_landlord_intents(lang="en"):
    """Return simplified INTENTS list for landlord flow."""
    return [
        ("enroll",     t("intent_enroll",     lang)),
        ("assistance", t("intent_assistance", lang)),
        ("done",       t("intent_done",       lang)),
    ]

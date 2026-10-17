import { SimplePage } from '../components/page-layout';

export function PoliticaDePrivacidadPage() {
  return (
    <SimplePage title="Política de privacidad">
      <p>
        Energy Drip utiliza la información que proporcionas para gestionar tu cita y la atención
        asociada.
      </p>
      <article>
        <h2>Datos de la reserva</h2>
        <p>
          Recibimos tu nombre, apellido, teléfono, correo opcional, servicio, profesional, horario y
          mensaje de coordinación. Estos datos permiten registrar la cita y contactar contigo si hay
          cambios.
        </p>
      </article>
      <article>
        <h2>Consentimientos informados</h2>
        <p>
          Si tu atención requiere un consentimiento, el equipo te compartirá un enlace privado para
          leer la información, responder las preguntas y firmar. Las respuestas, la firma y el
          documento generado se conservan como parte del registro de tu atención.
        </p>
      </article>
      <article>
        <h2>Acceso y almacenamiento</h2>
        <p>
          El personal autorizado accede a las reservas y documentos desde el panel privado. Los
          consentimientos no forman parte del catálogo público. No publiques ni compartas el enlace
          privado de tu consentimiento con otras personas.
        </p>
      </article>
      <article>
        <h2>Consultas sobre tus datos</h2>
        <p>
          Puedes solicitar al equipo de Energy Drip información sobre tus datos, su corrección o su
          eliminación. El equipo evaluará la solicitud y te informará cuando algún registro deba
          conservarse por su relación con la atención prestada.
        </p>
      </article>
      <p className="simple-page__note">
        No incluyas antecedentes médicos ni documentos de identidad en el mensaje de reserva. Usa
        únicamente el formulario privado que el equipo te indique.
      </p>
    </SimplePage>
  );
}

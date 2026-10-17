import { SimplePage } from '../components/page-layout';

const FAQS = [
  {
    question: '¿Cómo firmo mi consentimiento?',
    answer:
      'El equipo te comparte un enlace privado antes de tu cita; lo abres y firmas desde tu dispositivo.',
  },
  {
    question: '¿Qué pasa si mis respuestas requieren revisión?',
    answer: 'Un profesional de la clínica las revisa antes de confirmar tu tratamiento.',
  },
];

export function PreguntasFrecuentesPage() {
  return (
    <SimplePage title="Preguntas frecuentes">
      {FAQS.map((faq) => (
        <article key={faq.question}>
          <h3>{faq.question}</h3>
          <p>{faq.answer}</p>
        </article>
      ))}
    </SimplePage>
  );
}

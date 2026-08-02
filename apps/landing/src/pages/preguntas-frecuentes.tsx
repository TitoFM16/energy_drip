import { SimplePage } from '../components/page-layout';

const FAQS = [
  {
    question: '¿Cómo firmo mi consentimiento?',
    answer: 'Recibes un enlace por WhatsApp antes de tu cita; lo abres y firmas con el dedo.',
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
        <div key={faq.question}>
          <h3 className="font-semibold text-slate-900">{faq.question}</h3>
          <p>{faq.answer}</p>
        </div>
      ))}
    </SimplePage>
  );
}

import { useNavigate, useParams } from 'react-router-dom';
import { SignaturePad } from '../../features/signature-pad/signature-pad';
import { useConsentFlow } from '../../features/submission/use-consent-flow';

export function SignaturePage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { setSignatureSvg } = useConsentFlow();

  function handleCapture(svg: string) {
    setSignatureSvg(svg);
    navigate(`/c/${token}/review`);
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold text-slate-900">Firma con tu dedo</h1>
      <p className="text-sm text-slate-500">Dibuja tu firma en el recuadro de abajo.</p>
      <SignaturePad onCapture={handleCapture} />
    </div>
  );
}

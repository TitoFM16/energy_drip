import { Button, ErrorText, TextField } from '@medical-platform/ui';
import { useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import {
  useCreateTreatmentDefinition,
  useTreatmentDefinitions,
  useUpdateTreatmentDefinition,
} from '../../features/treatments/use-treatment-definitions';
import type { TreatmentDefinition } from '../../features/treatments/types';
import { PageHeading } from '../../shared/components/app-shell';
import { apiFetch, mediaUrl } from '../../shared/utilities/api';

const EMPTY_SERVICE = {
  name: '',
  description: '',
  price: '',
  currency: 'COP',
  duration_minutes: 60,
  image_url: '',
};
const priceLabel = (service: TreatmentDefinition) =>
  new Intl.NumberFormat('es-CO', { style: 'currency', currency: service.currency }).format(
    Number(service.price),
  );

export function TreatmentsPage() {
  const definitions = useTreatmentDefinitions(true);
  const createDefinition = useCreateTreatmentDefinition();
  const updateDefinition = useUpdateTreatmentDefinition();
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_SERVICE);
  const [image, setImage] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

  function resetForm() {
    setEditingId(null);
    setForm(EMPTY_SERVICE);
    setImage(null);
    setError('');
    if (fileRef.current) fileRef.current.value = '';
  }
  function edit(service: TreatmentDefinition) {
    setEditingId(service.id);
    setForm({
      name: service.name,
      description: service.description ?? '',
      price: service.price,
      currency: service.currency,
      duration_minutes: service.duration_minutes,
      image_url: service.image_url ?? '',
    });
    setImage(null);
    setError('');
    setSaved('');
    if (fileRef.current) fileRef.current.value = '';
    formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  async function handleSave(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setSaved('');
    try {
      if (
        image &&
        (!['image/jpeg', 'image/png', 'image/webp'].includes(image.type) ||
          image.size > 5 * 1024 * 1024)
      ) {
        setError('La imagen debe ser JPG, PNG o WebP y pesar máximo 5 MB.');
        return;
      }
      const input = {
        ...form,
        name: form.name.trim(),
        description: form.description.trim(),
        image_url: form.image_url.trim() || null,
      };
      const service = editingId
        ? await updateDefinition.mutateAsync({ ...input, definitionId: editingId })
        : await createDefinition.mutateAsync(input);
      setEditingId(service.id);
      if (image) {
        const body = new FormData();
        body.append('file', image);
        await apiFetch(`/api/v1/treatments/definitions/${service.id}/image`, {
          method: 'POST',
          body,
        });
        await queryClient.invalidateQueries({ queryKey: ['treatment-definitions'] });
      }
      resetForm();
      setSaved('Servicio guardado. Los cambios ya están disponibles en la página pública.');
    } catch {
      setError(
        'No se pudieron guardar todos los cambios. Revisa los datos y la imagen e inténtalo de nuevo.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeading>Servicios</PageHeading>
      <p className="mb-6 text-slate-600">
        Administra los servicios, precios e imágenes que ven tus clientes. La duración determina los
        horarios que pueden reservar.
      </p>
      {definitions.isLoading && <p>Cargando servicios…</p>}
      {definitions.isError && <ErrorText>No se pudo cargar el catálogo.</ErrorText>}
      {definitions.data?.length === 0 && (
        <p className="mb-6 rounded-lg bg-white p-5 text-slate-600">
          Agrega tu primer servicio para comenzar a recibir reservas.
        </p>
      )}
      {saved && (
        <p role="status" className="mb-4 rounded-lg bg-green-50 p-3 text-green-800">
          {saved}
        </p>
      )}
      <div className="mb-8 grid gap-4 xl:grid-cols-2">
        {definitions.data?.map((service) => (
          <article
            key={service.id}
            className="flex flex-wrap gap-4 rounded-xl border border-slate-200 bg-white p-4"
          >
            {service.image_url && (
              <img
                src={mediaUrl(service.image_url)}
                alt={service.name}
                className="h-24 w-24 rounded-lg object-cover"
              />
            )}
            <div className="min-w-0 flex-1">
              <h2 className="font-semibold">{service.name}</h2>
              <p className="mt-1 text-sm text-slate-500">
                {service.description || 'Sin descripción'}
              </p>
              <p className="mt-2 text-sm font-medium">
                {priceLabel(service)} {service.currency} · {service.duration_minutes} min
              </p>
              <p
                className={`mt-1 text-xs ${service.is_active ? 'text-green-700' : 'text-amber-700'}`}
              >
                {service.is_active ? 'Visible para reservar' : 'Archivado'}
              </p>
            </div>
            <div className="flex w-full gap-3">
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={busy}
                onClick={() => edit(service)}
              >
                Editar {service.name}
              </Button>
              <button
                type="button"
                disabled={busy || updateDefinition.isPending}
                onClick={() => {
                  setSaved('');
                  updateDefinition.mutate({
                    definitionId: service.id,
                    is_active: !service.is_active,
                  });
                }}
                className="text-sm text-slate-600 underline disabled:opacity-40"
              >
                {service.is_active ? 'Archivar' : 'Reactivar'}
              </button>
            </div>
          </article>
        ))}
      </div>
      {updateDefinition.isError && (
        <ErrorText className="mb-3">No se pudo actualizar el servicio.</ErrorText>
      )}
      <form
        ref={formRef}
        onSubmit={handleSave}
        className="max-w-3xl rounded-xl border border-slate-200 bg-white p-5"
      >
        <h2 className="mb-5 text-lg font-semibold">
          {editingId ? 'Editar servicio' : 'Agregar servicio'}
        </h2>
        <fieldset disabled={busy} className="grid gap-4 sm:grid-cols-2">
          <TextField
            label="Nombre del servicio"
            required
            maxLength={150}
            value={form.name}
            onChange={(event) => setForm({ ...form, name: event.target.value })}
          />
          <TextField
            label="Duración (minutos)"
            type="number"
            min={5}
            max={480}
            required
            value={form.duration_minutes}
            onChange={(event) => setForm({ ...form, duration_minutes: Number(event.target.value) })}
          />
          <TextField
            label="Precio"
            type="number"
            min={0}
            step="0.01"
            required
            value={form.price}
            onChange={(event) => setForm({ ...form, price: event.target.value })}
          />
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
            Moneda
            <select
              className="rounded-lg border border-slate-300 px-3 py-2"
              value={form.currency}
              onChange={(event) => setForm({ ...form, currency: event.target.value })}
            >
              <option value="COP">COP · Peso colombiano</option>
              <option value="USD">USD · Dólar estadounidense</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 sm:col-span-2">
            Descripción
            <textarea
              rows={3}
              maxLength={4000}
              className="rounded-lg border border-slate-300 px-3 py-2"
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
            />
          </label>
          <label className="flex flex-col gap-2 text-sm font-medium text-slate-700 sm:col-span-2">
            Imagen del servicio
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(event) => setImage(event.target.files?.[0] ?? null)}
            />
            <span className="text-xs font-normal text-slate-500">
              JPG, PNG o WebP. Máximo 5 MB. La imagen nueva reemplaza la anterior al guardar.
            </span>
          </label>
          {form.image_url && (
            <div className="flex items-center gap-4 sm:col-span-2">
              <img
                src={mediaUrl(form.image_url)}
                alt="Imagen actual del servicio"
                className="h-24 w-32 rounded-lg object-cover"
              />
              <button
                type="button"
                className="text-sm underline"
                onClick={() => setForm({ ...form, image_url: '' })}
              >
                Quitar imagen actual
              </button>
            </div>
          )}
          <div className="flex gap-3 sm:col-span-2">
            <Button type="submit">
              {busy ? 'Guardando…' : editingId ? 'Guardar cambios' : 'Agregar servicio'}
            </Button>
            {editingId && (
              <Button type="button" variant="secondary" onClick={resetForm}>
                Cancelar edición
              </Button>
            )}
          </div>
        </fieldset>
        {error && <ErrorText className="mt-3">{error}</ErrorText>}
      </form>
      <p className="mt-4 text-sm text-slate-500">
        Archivar retira el servicio del catálogo y conserva sus citas anteriores.
      </p>
    </div>
  );
}

import { Button, ErrorText, TextField } from '@medical-platform/ui';
import { useState } from 'react';
import {
  useContacts,
  useCreateContact,
  useCreateEmergencyContact,
  useDeleteContact,
  useDeleteEmergencyContact,
  useEmergencyContacts,
} from '../../features/patients/use-contacts';

interface ContactsSectionProps {
  patientId: string;
}

export function ContactsSection({ patientId }: ContactsSectionProps) {
  return (
    <section className="mt-6">
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
        Contactos
      </h2>
      <div className="flex flex-col gap-4">
        <PatientContactsSubsection patientId={patientId} />
        <EmergencyContactsSubsection patientId={patientId} />
      </div>
    </section>
  );
}

function PatientContactsSubsection({ patientId }: ContactsSectionProps) {
  const contacts = useContacts(patientId);
  const createContact = useCreateContact();
  const deleteContact = useDeleteContact();
  const [label, setLabel] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');

  async function handleAdd(event: React.FormEvent) {
    event.preventDefault();
    if (!label.trim()) return;
    await createContact.mutateAsync({
      patient_id: patientId,
      label: label.trim(),
      phone_number: phone.trim() || undefined,
      email: email.trim() || undefined,
    });
    setLabel('');
    setPhone('');
    setEmail('');
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-medium text-slate-700">Otros contactos</h3>
      <ul className="mb-3 flex flex-col gap-2">
        {contacts.data?.map((contact) => (
          <li
            key={contact.id}
            className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm"
          >
            <span className="text-slate-800">
              {contact.label}
              {contact.phone_number ? ` · ${contact.phone_number}` : ''}
              {contact.email ? ` · ${contact.email}` : ''}
            </span>
            <button
              type="button"
              disabled={deleteContact.isPending}
              onClick={() => deleteContact.mutate({ contactId: contact.id, patientId })}
              className="text-xs text-slate-500 underline disabled:opacity-40"
            >
              Eliminar
            </button>
          </li>
        ))}
        {contacts.data?.length === 0 && (
          <p className="text-sm text-slate-500">Sin otros contactos registrados.</p>
        )}
      </ul>
      <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-2">
        <TextField
          label="Etiqueta"
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Trabajo, casa..."
        />
        <TextField
          label="Teléfono"
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <TextField
          label="Correo electrónico"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Button type="submit" size="sm" disabled={!label.trim() || createContact.isPending}>
          {createContact.isPending ? 'Guardando...' : 'Agregar'}
        </Button>
      </form>
      {createContact.isError && <ErrorText className="mt-2">No se pudo guardar.</ErrorText>}
    </div>
  );
}

function EmergencyContactsSubsection({ patientId }: ContactsSectionProps) {
  const contacts = useEmergencyContacts(patientId);
  const createContact = useCreateEmergencyContact();
  const deleteContact = useDeleteEmergencyContact();
  const [fullName, setFullName] = useState('');
  const [relationship, setRelationship] = useState('');
  const [phone, setPhone] = useState('');

  async function handleAdd(event: React.FormEvent) {
    event.preventDefault();
    if (!fullName.trim() || !phone.trim()) return;
    await createContact.mutateAsync({
      patient_id: patientId,
      full_name: fullName.trim(),
      relationship: relationship.trim() || undefined,
      phone_number: phone.trim(),
    });
    setFullName('');
    setRelationship('');
    setPhone('');
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-medium text-slate-700">Contactos de emergencia</h3>
      <ul className="mb-3 flex flex-col gap-2">
        {contacts.data?.map((contact) => (
          <li
            key={contact.id}
            className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm"
          >
            <span className="text-slate-800">
              {contact.full_name}
              {contact.relationship ? ` · ${contact.relationship}` : ''} · {contact.phone_number}
            </span>
            <button
              type="button"
              disabled={deleteContact.isPending}
              onClick={() => deleteContact.mutate({ contactId: contact.id, patientId })}
              className="text-xs text-slate-500 underline disabled:opacity-40"
            >
              Eliminar
            </button>
          </li>
        ))}
        {contacts.data?.length === 0 && (
          <p className="text-sm text-slate-500">Sin contactos de emergencia registrados.</p>
        )}
      </ul>
      <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-2">
        <TextField
          label="Nombre completo"
          type="text"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
        <TextField
          label="Parentesco"
          type="text"
          value={relationship}
          onChange={(e) => setRelationship(e.target.value)}
        />
        <TextField
          label="Teléfono"
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <Button
          type="submit"
          size="sm"
          disabled={!fullName.trim() || !phone.trim() || createContact.isPending}
        >
          {createContact.isPending ? 'Guardando...' : 'Agregar'}
        </Button>
      </form>
      {createContact.isError && <ErrorText className="mt-2">No se pudo guardar.</ErrorText>}
    </div>
  );
}

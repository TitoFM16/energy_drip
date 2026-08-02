export interface BookingFormState {
  first_name: string;
  last_name: string;
  phone_number: string;
  email: string;
  treatment_definition_id: string;
  preferred_date: string;
  message: string;
  website: string;
}

export interface BookingRequestPayload {
  first_name: string;
  last_name: string;
  phone_number: string;
  email: string | null;
  treatment_definition_id: string;
  preferred_date: string | null;
  message: string | null;
  website: string;
}

/** Empty-string form fields mean "not provided" for the optional ones, but
 * the API expects null rather than "" for those — this is the one bit of
 * translation between form state and the request body worth testing on
 * its own. */
export function buildBookingRequestPayload(form: BookingFormState): BookingRequestPayload {
  return {
    first_name: form.first_name,
    last_name: form.last_name,
    phone_number: form.phone_number,
    email: form.email || null,
    treatment_definition_id: form.treatment_definition_id,
    preferred_date: form.preferred_date || null,
    message: form.message || null,
    website: form.website,
  };
}

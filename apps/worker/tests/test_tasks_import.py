def test_tasks_module_registers_actors():
    from medical_worker import tasks

    assert tasks.send_whatsapp.send_whatsapp_message.actor_name == "send_whatsapp_message"
    assert tasks.consent_request.start_consent_request.actor_name == "start_consent_request"

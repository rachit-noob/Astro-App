def test_message_returns_llm_response(send, llm):
    response = send("What should I focus on for my career?")

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "user-123"
    assert body["session_id"] == "session-1"
    assert body["response"] == "mock reply 1"
    assert body["fallback"] is False
    assert llm.calls[0]["user_message"] == "What should I focus on for my career?"


def test_blank_message_is_rejected(send):
    assert send("   ").status_code == 422


def test_memory_saved_in_one_session_is_used_in_a_new_session(send, llm):
    send(
        "I'm planning to switch jobs next year, and I prefer advice in Hindi.",
        session_id="session-1",
    )

    response = send("What do you remember about my career plans?", session_id="session-2")

    body = response.json()
    assert body["context_used"] == ["career_goal", "language_preference"]
    system_prompt = llm.calls[-1]["system_prompt"]
    assert "switch jobs next year" in system_prompt
    assert "language_preference: Hindi" in system_prompt
    assert llm.calls[-1]["history"] == []


def test_memory_in_the_same_message_is_used_immediately(send, llm):
    response = send("I'm planning to switch jobs next year. What should I focus on for my career?")

    assert "career_goal" in response.json()["context_used"]
    assert "switch jobs next year" in llm.calls[0]["system_prompt"]


def test_recent_history_supports_follow_up(send, llm):
    send("Should I change my job?")
    send("Why do you say that?")

    assert llm.calls[1]["history"] == [
        {"role": "user", "content": "Should I change my job?"},
        {"role": "assistant", "content": "mock reply 1"},
    ]


def test_history_is_limited_and_scoped_to_session(send, llm):
    for index in range(4):
        send(f"message {index}", session_id="busy")
    send("other session message", session_id="quiet")
    send("final", session_id="busy")

    busy_history = llm.calls[-1]["history"]
    assert len(busy_history) == 4
    assert [item["content"] for item in busy_history if item["role"] == "user"] == ["message 2", "message 3"]
    assert llm.calls[4]["history"] == []


def test_irrelevant_memories_are_excluded_from_context(send, llm):
    send("I love cricket and cooking.")
    send("I was born on 5 March 1995 in Delhi.")
    send("I'm planning to switch jobs next year.")

    response = send("What should I focus on for my career?")

    assert response.json()["context_used"] == ["career_goal"]
    system_prompt = llm.calls[-1]["system_prompt"]
    assert "switch jobs next year" in system_prompt
    assert "cricket" not in system_prompt
    assert "cooking" not in system_prompt
    assert "1995" not in system_prompt


def test_users_do_not_share_memories(send, llm):
    send("I'm planning to switch jobs next year.", user_id="alice")

    response = send("What do you remember about my career plans?", user_id="bob")

    assert response.json()["context_used"] == []
    assert "switch jobs" not in llm.calls[-1]["system_prompt"]


def test_correction_updates_existing_memory(send, client):
    send("I prefer advice in Hindi.")
    send("Actually I prefer advice in English.")

    memories = client.get("/users/user-123/memories").json()

    languages = [m for m in memories if m["category"] == "language_preference"]
    assert len(languages) == 1
    assert languages[0]["value"] == "English"


def test_questions_and_small_talk_are_not_stored(send, client):
    send("What should I focus on for my career?")
    send("Thanks, that was helpful!")

    assert client.get("/users/user-123/memories").json() == []


def test_llm_outage_returns_fallback_and_keeps_memory(send, client, llm):
    llm.available = False

    response = send("I'm planning to switch jobs next year. Any advice for my career?")

    body = response.json()
    assert response.status_code == 200
    assert body["fallback"] is True
    assert "switch jobs next year" in body["response"]
    memories = client.get("/users/user-123/memories").json()
    assert [m["category"] for m in memories] == ["career_goal"]

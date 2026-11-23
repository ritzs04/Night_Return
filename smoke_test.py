#!/usr/bin/env python3
"""
Night Return - API smoke test (Python 3 standard library only).

Run AFTER deploying the WAR and starting Tomcat:
    python3 scripts/smoke_test.py http://localhost:8080/night-return

It creates a fresh test user, verifies OTPs in demo mode (SMS_API_KEY unset),
then runs the main journey: register, contacts, journey, location, SOS, history, end.
Each step prints PASS or FAIL. Exit code is 0 only if everything passed.
"""
import http.cookiejar
import json
import random
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/night-return").rstrip("/") + "/api"
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
failures = []


def call(method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with opener.open(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8") or "{}")
        except Exception:
            return e.code, {}


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + (("  -> " + str(detail)) if detail and not cond else ""))
    if not cond:
        failures.append(name)
    return cond


def random_phone():
    return "9" + "".join(str(random.randint(0, 9)) for _ in range(9))


def verified_phone(kind):
    phone = random_phone()
    status, r = call("POST", "/send-otp", {"phone": phone, "type": kind})
    code = r.get("demoOtp")
    if not check(f"send-otp ({kind})", status == 200 and code, r):
        return None, None
    status, r = call("POST", "/verify-otp", {"phone": phone, "otp": code, "type": kind})
    check(f"verify-otp ({kind})", status == 200 and r.get("success"), r)
    return phone, code


# 1. Sign-up path
user_phone, _ = verified_phone("user_registration")
if user_phone:
    status, r = call("POST", "/register", {
        "username": "Smoke Tester", "email": f"smoke{random.randint(1000, 99999)}@example.com",
        "phoneNumber": user_phone, "address": "Test street", "password": "secret123", "codeWord": "sunflower"})
    check("register", status == 200 and r.get("success"), r)

    status, r = call("GET", "/user/profile")
    check("profile after register (session active)", status == 200 and r.get("success"), r)

    # Wrong password must be refused.
    status, r = call("POST", "/login", {"phone": user_phone, "password": "wrong-pass"})
    check("login with wrong password is refused", status == 401, (status, r))

    # 2. Contacts: each must be OTP-verified first
    c1, _ = verified_phone("contact_verification")
    c2, _ = verified_phone("contact_verification")
    if c1 and c2:
        status, r = call("POST", "/contacts/replace", {"contacts": [
            {"name": "Mom", "phone": c1}, {"name": "Dad", "phone": c2}]})
        check("save 2 verified contacts", status == 200 and r.get("success"), r)

        status, r = call("POST", "/contacts/replace", {"contacts": [
            {"name": "Stranger", "phone": random_phone()}, {"name": "Dad", "phone": c2}]})
        check("refuse an unverified contact number", status == 403, (status, r))

    # 3. Journey, tracking, SOS
    status, r = call("POST", "/journey/start", {
        "startingPoint": "Place A", "endingPoint": "Place B", "transportMode": "walk", "timerDuration": 5})
    jid = r.get("journeyId")
    check("start journey", status == 200 and jid, r)
    if jid:
        status, r = call("POST", "/location/update", {"journeyId": jid, "latitude": 12.97, "longitude": 77.59, "offline": False})
        check("location update", status == 200 and r.get("success"), r)

        status, r = call("POST", "/journey/extend-timer", {"journeyId": jid, "minutes": 10})
        check("extend timer", status == 200 and r.get("success"), r)

        status, r = call("POST", "/alert/trigger", {
            "journeyId": jid, "type": "emergency_button", "latitude": 12.97, "longitude": 77.59})
        check("SOS alert stored", status == 200 and r.get("alertId"), r)
        alert_id = r.get("alertId")

        status, r = call("GET", "/alert/history")
        check("alert appears in history", status == 200 and any(a.get("alertId") == alert_id for a in r.get("alerts", [])), r)

        if alert_id:
            status, r = call("POST", "/alert/resolve", {"alertId": alert_id})
            check("resolve alert", status == 200 and r.get("success"), r)

        status, r = call("POST", "/journey/end", {"journeyId": jid, "status": "completed"})
        check("end journey", status == 200 and r.get("success"), r)

        status, r = call("GET", "/journey/history")
        check("journey in history", status == 200 and any(j.get("journeyId") == jid for j in r.get("journeys", [])), r)

    # 4. Code word
    status, r = call("POST", "/verify-code-word", {"candidates": ["wrong word"]})
    check("wrong code word is refused", status == 200 and r.get("match") is False, (status, r))
    status, r = call("POST", "/verify-code-word", {"candidates": ["please help", "sunflower"]})
    check("right code word is accepted (as one of the spoken windows)", status == 200 and r.get("match") is True, (status, r))

    # 5. Logout, then login again
    call("POST", "/logout", {})
    status, r = call("GET", "/user/profile")
    check("profile refused after logout", status == 401, (status, r))
    status, r = call("POST", "/login", {"phone": user_phone, "password": "secret123"})
    check("login after logout", status == 200 and r.get("success"), r)

print()
print("ALL PASSED" if not failures else f"{len(failures)} FAILED: " + ", ".join(failures))
sys.exit(0 if not failures else 1)

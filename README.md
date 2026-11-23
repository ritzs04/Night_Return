# Night Return - Backend (Java Servlets + JDBC + MySQL)

## What is in this folder
```
backend/
├── pom.xml                      Maven build (WAR), Java 8+ compatible
├── sql/schema.sql               MySQL 8 schema (run once)
└── src/main/
    ├── java/com/nightsafety/
    │   ├── db/Db.java           JDBC connection (reads env vars)
    │   ├── util/Security.java   BCrypt hashing, OTP generation
    │   ├── service/OtpService.java   Server-side OTP + SMS sending
    │   ├── service/AlertService.java Builds alert text, texts contacts
    │   ├── web/Http.java        JSON helpers
    │   └── api/
    │       ├── ApiServlet.java  Single entry point for /api/*
    │       ├── AuthApi.java     OTP, register, login, profile, code word, contacts
    │       └── JourneyApi.java  Journeys, timer, location, alerts
    └── webapp/
        ├── index.html           Front end (set BACKEND = true before deploying)
        ├── sw.js                Service worker (offline app shell)
        └── WEB-INF/web.xml
```

## 1. Database
```bash
mysql -u root -p < sql/schema.sql
```

## 2. Configure (environment variables, never in code)
| Variable | Example | Purpose |
|---|---|---|
| `DB_URL` | `jdbc:mysql://localhost:3306/night_safety_db?useSSL=false&serverTimezone=UTC` | Database URL (optional, default is shown) |
| `DB_USER` | `root` | Database user |
| `DB_PASSWORD` | `your_password` | Database password |
| `SMS_API_KEY` | `xxxx` | SMS gateway key. **If unset, OTPs are returned to the page (demo mode).** |
| `SMS_API_URL` | `https://www.fast2sms.com/dev/bulkV2` | SMS gateway endpoint (optional) |

Set them before starting Tomcat, for example:
- Windows: `set DB_PASSWORD=your_password`
- Linux/Mac: `export DB_PASSWORD=your_password`

## 3. Build and deploy
```bash
mvn clean package          # produces target/night-return.war
cp target/night-return.war $TOMCAT_HOME/webapps/
$TOMCAT_HOME/bin/catalina.sh run    # or catalina.bat run on Windows
```
Open `http://localhost:8080/night-return/`.

For the front end to talk to the server, set `const BACKEND=true;` in `index.html` before building the WAR (it is `false` in the preview).

## 4. Test checklist
1. Splash, accept permissions, enter a 10-digit phone, Send OTP. In demo mode the code appears in the top banner.
2. Verify the OTP, then register. The server checks the phone was verified in the last 30 minutes.
3. Add two contacts. Each must be verified by OTP before saving; the server enforces this.
4. Start a journey. Check `SELECT * FROM journeys;` and `journey_tracking` rows appearing.
5. Trigger SOS. With `SMS_API_KEY` set, the contacts receive a text with a map link. Check `SELECT * FROM alerts;`.
6. Log out and log back in with phone and password.

## Security notes (for the viva)
- OTPs are generated on the server, stored only as BCrypt hashes, expire after 10 minutes, and lock after 5 wrong tries.
- Passwords and code words are BCrypt-hashed. The code word is checked on the server.
- Every journey, location and alert query is scoped to the logged-in user (`user_id` check).
- All SQL uses prepared statements.
- Session cookies are HTTP-only. Use HTTPS in production.

## Known limits
- OTP requests are not rate-limited per IP yet (plan Section 9.3). Add a counter table before a public launch.
- Profile pictures are stored as base64 text in the `users` table, capped at about 300 KB each.
- The safety photo from "I'm Safe" is kept in the browser only.

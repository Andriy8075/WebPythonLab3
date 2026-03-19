To launch project:

1. Launch Docker on your local machine.
2. Run:

```bash
git clone https://github.com/Andriy8075/WebPythonLab3.git
cd WebPythonLab3
docker compose up --build
```
3. Open http://localhost:8080 in browser.

The app uses MongoDB for data storage. Collections: `users`, `charity_campaigns`, `donations`, `comments`.
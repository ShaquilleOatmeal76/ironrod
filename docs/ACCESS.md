# Reaching Iron Rod from anywhere (and installing it as an app)

## 1. Private HTTPS over Tailscale (do this first)

Phones only offer **Install / Add to Home Screen** as a real app (full screen,
offline reading) when the page is served over **HTTPS**. Tailscale can give the
server a real certificate on your tailnet with one command.

On the server:

```bash
sudo tailscale serve --bg 8642
```

The first time, it may print a link to turn on **HTTPS certificates** for your
tailnet. Open it, enable HTTPS, then run the command again. It prints the
address, something like:

```
https://minas-tirith.<your-tailnet>.ts.net
```

That's the address to use on every device from now on. `--bg` keeps it running
across reboots. To check it: `tailscale serve status`. To stop it:
`sudo tailscale serve --https=443 off`.

Nothing is opened to the internet: only devices signed in to your tailnet can
reach it.

## 2. Install it on a phone

- **iPhone (Safari):** open the address → **Share** → **Add to Home Screen**.
- **Android (Chrome):** open the address → **Install app** (or ⋮ → Install).
- **Desktop (Chrome/Edge):** the install icon in the address bar, or press
  ⌘K in Iron Rod and run **Install Iron Rod as an app**.

Once installed it opens full screen from its own icon. Chapters, talks and the
library you've opened stay readable offline; notes and highlights need the
server.

## 3. Family outside your house (later)

Two options:

- **Invite them to your tailnet** (Tailscale → Users → Invite). Easiest today;
  each person installs the Tailscale app once.
- **Cloudflare Tunnel + Cloudflare Access** with your own domain, e.g.
  `ironrod.bigelow.family`. No app to install; family sign in with an emailed
  code. Your home IP stays hidden and no router ports are opened.

> Don't expose Iron Rod to the public internet before family accounts exist.
> Right now there are no logins inside Iron Rod itself, so anyone who can reach
> it can read and edit. Tailscale (or Cloudflare Access in front) is what keeps
> it private.

## Backups

Everything you write lives in `./data/ironrod.db` next to `docker-compose.yml`.
A simple nightly copy (SQLite-safe, works while the app runs):

```bash
sqlite3 /srv/docker/ironrod/data/ironrod.db ".backup '/srv/backups/ironrod-$(date +%F).db'"
```

Put that in `crontab -e` as `0 3 * * * …` and keep a few weeks of copies.

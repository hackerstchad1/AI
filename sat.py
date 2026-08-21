#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║    SAT  –  Satellite Aerial Toolkit                                 ║
    ║    Projet éducatif / Ethical Hacking                                ║
    ║    Visualisation de cartes satellites publiques & géocodage         ║
    ║    Créé avec passion par la communauté NULLSEC (Tchad)              ║
    ╚═══════════════════════════════════════════════════════════════════════╝

    Avertissement éthique / légal :
    ─────────────────────────────────
    Ce script est fourni uniquement à des fins éducatives, de recherche en
    cybersécurité défensive et de démonstration de l'utilisation d'API
    géospatiales ouvertes. Il n'accède à aucune donnée militaire, privée ou
    protégée. L'utilisateur est seul responsable de son utilisation légale.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote

import requests
import folium
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text
from geopy.geocoders import Nominatim

# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════
console = Console()

APP_NAME = "SAT"
APP_VERSION = "2.0.0"
APP_AUTHOR = "NULLSEC (Tchad)"
APP_MOTTO = "Observer le monde, protéger les données."

SATELLITE_TILES = {
    "esri": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    "carto_dark": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
}

MAP_URLS = {
    "osm": "https://www.openstreetmap.org/search?query={query}#map=15/{lat}/{lon}",
    "bing_aerial": "https://www.bing.com/maps?cp={lat}~{lon}&lvl=17&style=a",
    "google": "https://www.google.com/maps/search/?api=1&query={lat},{lon}",
}

NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search"
REVERSE_NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/reverse"
ISS_ENDPOINT = "https://api.open-notify.org/iss-now.json"

GEOCODER = Nominatim(user_agent=f"{APP_NAME}/{APP_VERSION} ({APP_AUTHOR})")

# ═══════════════════════════════════════════════════════════════════════════
# Utilitaires visuels
# ═══════════════════════════════════════════════════════════════════════════

def clear_screen() -> None:
    """Nettoie le terminal selon l'OS."""
    os.system("cls" if os.name == "nt" else "clear")


def banner() -> None:
    """Affiche la bannière ASCII stylisée."""
    art = """
    ███████╗ █████╗ ████████╗
    ██╔════╝██╔══██╗╚══██╔══╝
    ███████╗███████║   ██║
    ╚════██║██╔══██║   ██║
    ███████║██║  ██║   ██║
    ╚══════╝╚═╝  ╚═╝   ╚═╝
    """
    console.print(Panel(
        Text(art, style="bold cyan") + "\n" +
        Text(f"{APP_NAME} v{APP_VERSION} — {APP_MOTTO}", style="bold green") + "\n" +
        Text(f"Auteur : {APP_AUTHOR}", style="dim"),
        title="[bold red]NULLSEC[/bold red]",
        subtitle="[dim]Ethical Hacking | OSINT | Geospatial[/dim]",
        border_style="bright_magenta",
        padding=(1, 4),
    ))


def progress_bar(task_name: str, steps: int = 25, delay: float = 0.08) -> None:
    """Affiche une barre de progression animée dans le terminal."""
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40, complete_style="green", finished_style="bright_green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task(f"[cyan]{task_name}...", total=steps)
        for _ in range(steps):
            time.sleep(delay)
            progress.advance(task)


def show_menu() -> str:
    """Affiche le menu interactif et retourne le choix de l'utilisateur."""
    table = Table(title="Menu principal", title_style="bold cyan", border_style="blue")
    table.add_column("#", style="bold yellow", justify="center")
    table.add_column("Action", style="white")
    table.add_column("Description", style="dim")

    options = [
        ("1", "Localiser une adresse", "Géocode une adresse puis ouvre la carte satellite"),
        ("2", "Coordonnées GPS", "Ouvre une carte satellite depuis latitude/longitude"),
        ("3", "Position ISS", "Affiche la position en temps réel de la Station Spatiale Internationale"),
        ("4", "Générer un rapport", "Exporte un rapport Markdown de la dernière requête"),
        ("5", "À propos", "Informations sur le projet et liens utiles"),
        ("0", "Quitter", "Ferme SAT proprement"),
    ]
    for num, action, desc in options:
        table.add_row(num, action, desc)

    console.print(table)
    return console.input("\n[bold green]Votre choix » [/bold green]").strip()


# ═══════════════════════════════════════════════════════════════════════════
# Services géospatiaux
# ═══════════════════════════════════════════════════════════════════════════

def geocode_address(address: str) -> dict | None:
    """Géocode une adresse via Nominatim (OpenStreetMap)."""
    headers = {"User-Agent": f"{APP_NAME}/{APP_VERSION} ({APP_AUTHOR})"}
    params = {"q": address, "format": "json", "limit": 1}
    try:
        resp = requests.get(NOMINATIM_ENDPOINT, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            console.print("[red]Adresse introuvable.[/red]")
            return None
        return {
            "display_name": data[0]["display_name"],
            "lat": float(data[0]["lat"]),
            "lon": float(data[0]["lon"]),
            "osm_id": data[0].get("osm_id"),
            "type": data[0].get("type"),
        }
    except requests.RequestException as exc:
        console.print(f"[red]Erreur réseau : {exc}[/red]")
        return None


def reverse_geocode(lat: float, lon: float) -> dict | None:
    """Effectue un géocodage inversé (coord → adresse)."""
    headers = {"User-Agent": f"{APP_NAME}/{APP_VERSION} ({APP_AUTHOR})"}
    params = {"lat": lat, "lon": lon, "format": "json"}
    try:
        resp = requests.get(REVERSE_NOMINATIM_ENDPOINT, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("display_name") or "Adresse non disponible"
    except requests.RequestException as exc:
        console.print(f"[red]Erreur réseau : {exc}[/red]")
        return None


def get_iss_position() -> dict | None:
    """Récupère la position actuelle de l'ISS."""
    try:
        resp = requests.get(ISS_ENDPOINT, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {
            "lat": float(data["iss_position"]["latitude"]),
            "lon": float(data["iss_position"]["longitude"]),
            "timestamp": data["timestamp"],
        }
    except requests.RequestException as exc:
        console.print(f"[red]Erreur réseau : {exc}[/red]")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Cartographie
# ═══════════════════════════════════════════════════════════════════════════

def build_local_map(lat: float, lon: float, marker_title: str = "Cible", provider: str = "esri") -> Path:
    """Génère une carte HTML satellite locale via Folium et retourne le chemin."""
    tile_url = SATELLITE_TILES.get(provider, SATELLITE_TILES["esri"])
    tile_attr = "Esri World Imagery" if provider == "esri" else "CartoDB"
    m = folium.Map(location=[lat, lon], zoom_start=16, tiles=tile_url, attr=tile_attr)
    folium.Marker(
        [lat, lon],
        popup=marker_title,
        tooltip=f"lat={lat}, lon={lon}",
        icon=folium.Icon(color="red", icon="crosshairs", prefix="fa"),
    ).add_to(m)
    folium.Circle([lat, lon], radius=500, color="red", fill=True, fill_opacity=0.15).add_to(m)
    path = Path("satellite_map.html")
    m.save(str(path))
    return path


def open_map(lat: float, lon: float, provider: str = "bing_aerial", query: str = "") -> None:
    """Ouvre le navigateur par défaut sur une carte satellite (locale ou web)."""
    if provider == "local":
        progress_bar("Génération de la carte satellite locale")
        html_path = build_local_map(lat, lon, marker_title=query or "Position")
        url = html_path.resolve().as_uri()
        console.print(f"\n[bold yellow]Ouverture de la carte satellite locale...[/bold yellow]")
    else:
        if provider not in MAP_URLS:
            provider = "bing_aerial"
        url = MAP_URLS[provider].format(lat=lat, lon=lon, query=quote(query))
        console.print(f"\n[bold yellow]Ouverture de la carte ({provider})...[/bold yellow]")
    console.print(f"[dim]{url}[/dim]\n")
    webbrowser.open(url)


def show_location_summary(info: dict, source: str = "geocoding") -> None:
    """Affiche un résumé enrichi des données localisées."""
    table = Table(title="Résultat de localisation", title_style="bold green", border_style="green")
    table.add_column("Clé", style="cyan")
    table.add_column("Valeur", style="white")
    table.add_row("Source", source)
    table.add_row("Nom / Adresse", info.get("display_name", "N/A"))
    table.add_row("Latitude", str(info.get("lat", "N/A")))
    table.add_row("Longitude", str(info.get("lon", "N/A")))
    if "type" in info:
        table.add_row("Type OSM", str(info["type"]))
    if "osm_id" in info:
        table.add_row("OSM ID", str(info["osm_id"]))
    console.print(table)


# ═══════════════════════════════════════════════════════════════════════════
# Rapport
# ═══════════════════════════════════════════════════════════════════════════

def generate_report(data: dict, filename: str = "rapport_sat.md") -> Path:
    """Génère un rapport Markdown de la session."""
    path = Path(filename)
    content = f"""# Rapport SAT — {APP_NAME} v{APP_VERSION}

**Auteur du projet** : {APP_AUTHOR}  
**Date** : {time.strftime("%Y-%m-%d %H:%M:%S")}

## Données collectées

| Clé | Valeur |
|-----|--------|
| Source | {data.get('source', 'N/A')} |
| Nom / Adresse | {data.get('display_name', 'N/A')} |
| Latitude | {data.get('lat', 'N/A')} |
| Longitude | {data.get('lon', 'N/A')} |

## Liens directs

- [OpenStreetMap](https://www.openstreetmap.org/#map=15/{data.get('lat',0)}/{data.get('lon',0)})
- [Bing Maps Aerial](https://www.bing.com/maps?cp={data.get('lat',0)}~{data.get('lon',0)}&lvl=17&style=a)
- [Google Maps](https://www.google.com/maps/search/?api=1&query={data.get('lat',0)},{data.get('lon',0)})

## Avertissement légal

Ce rapport a été généré par un outil éducatif. Les données proviennent de
services publics (OpenStreetMap, Open-Notify, Bing/Google Maps publics). Toute
utilisation doit respecter les lois locales et la vie privée des personnes.
"""
    path.write_text(content, encoding="utf-8")
    return path


# ═══════════════════════════════════════════════════════════════════════════
# Flux principal
# ═══════════════════════════════════════════════════════════════════════════

last_result: dict | None = None


def action_geocode_address() -> None:
    global last_result
    address = console.input("[bold cyan]Adresse à localiser : [/bold cyan]").strip()
    if not address:
        console.print("[red]Adresse vide.[/red]")
        return
    progress_bar("Géocodage de l'adresse")
    result = geocode_address(address)
    if result:
        result["source"] = "Géocodage adresse"
        show_location_summary(result)
        last_result = result
        if console.input("\n[bold green]Ouvrir la carte satellite ? [O/n] : [/bold green]").lower() in ("", "o", "y", "yes"):
            open_map(result["lat"], result["lon"], provider="bing_aerial", query=address)


def action_coordinates() -> None:
    global last_result
    try:
        lat = float(console.input("[bold cyan]Latitude  : [/bold cyan]").strip().replace(",", "."))
        lon = float(console.input("[bold cyan]Longitude : [/bold cyan]").strip().replace(",", "."))
    except ValueError:
        console.print("[red]Coordonnées invalides.[/red]")
        return
    progress_bar("Résolution de la position")
    address = reverse_geocode(lat, lon)
    result = {
        "lat": lat,
        "lon": lon,
        "display_name": address or "Coordonnées manuelles",
        "source": "Coordonnées GPS",
    }
    show_location_summary(result)
    last_result = result
    if console.input("\n[bold green]Ouvrir la carte satellite ? [O/n] : [/bold green]").lower() in ("", "o", "y", "yes"):
        open_map(lat, lon, provider="bing_aerial")


def action_iss() -> None:
    global last_result
    progress_bar("Récupération de la position ISS")
    iss = get_iss_position()
    if not iss:
        return
    result = {
        "lat": iss["lat"],
        "lon": iss["lon"],
        "display_name": "Station Spatiale Internationale (ISS)",
        "source": "Open-Notify ISS API",
    }
    show_location_summary(result)
    last_result = result
    if console.input("\n[bold green]Ouvrir la carte satellite ? [O/n] : [/bold green]").lower() in ("", "o", "y", "yes"):
        open_map(iss["lat"], iss["lon"], provider="bing_aerial", query="ISS")


def action_report() -> None:
    if not last_result:
        console.print("[red]Aucune donnée à exporter. Effectuez d'abord une localisation.[/red]")
        return
    progress_bar("Génération du rapport")
    path = generate_report(last_result)
    console.print(f"[bold green]Rapport sauvegardé : {path.resolve()}[/bold green]")


def action_about() -> None:
    about_text = f"""
    [bold cyan]{APP_NAME} v{APP_VERSION}[/bold cyan]
    {APP_MOTTO}

    [bold]Auteur :[/bold] {APP_AUTHOR}
    [bold]Licence :[/bold] Éducative / Recherche en cybersécurité défensive

    [bold]Liens utiles :[/bold]
    • OpenStreetMap Nominatim : https://nominatim.org/
    • Open-Notify ISS API     : http://open-notify.org/
    • Bing Maps               : https://www.bing.com/maps
    • Google Maps             : https://maps.google.com
    • NULLSEC (Tchad)         : https://github.com/nullsec-td (exemple)

    [bold red]Rappel éthique :[/bold red] ce logiciel est strictement éducatif.
    """
    console.print(Panel(about_text, title="À propos", border_style="bright_magenta"))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sat",
        description="SAT — Satellite Aerial Toolkit (éducatif / ethical hacking)",
        epilog="Exemple : python sat.py --address 'N'Djamena, Tchad'",
    )
    parser.add_argument("--address", "-a", help="Adresse à géocoder et afficher sur carte")
    parser.add_argument("--lat", type=float, help="Latitude")
    parser.add_argument("--lon", type=float, help="Longitude")
    parser.add_argument("--provider", "-p", choices=list(MAP_URLS.keys()), default="bing_aerial", help="Fournisseur de carte")
    parser.add_argument("--iss", action="store_true", help="Afficher la position ISS")
    args = parser.parse_args()

    banner()

    # Mode CLI rapide
    if args.iss:
        progress_bar("Récupération ISS")
        iss = get_iss_position()
        if iss:
            show_location_summary({**iss, "display_name": "ISS", "source": "Open-Notify ISS API"})
            open_map(iss["lat"], iss["lon"], provider=args.provider, query="ISS")
        return

    if args.address:
        progress_bar("Géocodage")
        result = geocode_address(args.address)
        if result:
            result["source"] = "CLI"
            show_location_summary(result)
            open_map(result["lat"], result["lon"], provider=args.provider, query=args.address)
        return

    if args.lat is not None and args.lon is not None:
        progress_bar("Chargement de la carte")
        show_location_summary({
            "lat": args.lat,
            "lon": args.lon,
            "display_name": reverse_geocode(args.lat, args.lon) or "Coordonnées manuelles",
            "source": "CLI",
        })
        open_map(args.lat, args.lon, provider=args.provider)
        return

    # Mode interactif
    while True:
        try:
            choice = show_menu()
            if choice == "1":
                action_geocode_address()
            elif choice == "2":
                action_coordinates()
            elif choice == "3":
                action_iss()
            elif choice == "4":
                action_report()
            elif choice == "5":
                action_about()
            elif choice == "0":
                console.print("\n[bold green]Fermeture de SAT. À bientôt ! 🛰[/bold green]\n")
                sys.exit(0)
            else:
                console.print("[red]Choix invalide.[/red]")
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Interrompu par l'utilisateur.[/bold yellow]")
            sys.exit(0)


if __name__ == "__main__":
    main()

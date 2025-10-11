#!/usr/bin/env python3
import argparse
import os
import requests
import urllib3
import time
from datetime import datetime
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv
from pathlib import Path

# Load .env from script directory
#load_dotenv(dotenv_path=Path(__file__).parent / ".env")
#load_dotenv("/opt/htb-cli/.env")

with open("/opt/htb-cli/.env", 'r') as t:
    for line in t:
        if line.strip().startswith("token="):
            token = line.strip().split("=", 1)[1]
            break
    else:
        raise ValueError("Token not found in /opt/htb-cli/.env")

# Disable HTTPS warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Get API token
#token = os.getenv("token")
if not token:
    raise ValueError("Token not found (check .env or $token)")

headers = {
    "Authorization": f"Bearer {token}",
    "User-Agent": "Profzzor Python Script"
}

proxy = {
    "https":"http://127.0.0.1:8080",
}

class HTBClient:
    def __init__(self):
        self.console = Console()

    def _get(self, endpoint):
        try:
            r = requests.get(f"https://labs.hackthebox.com/api/v4/{endpoint}",
                             headers=headers, verify=False)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            self.console.print(f"[red]GET /{endpoint} failed: {e}[/red]")
            return None

    def _post(self, endpoint, data=None):
        try:
            r = requests.post(f"https://labs.hackthebox.com/api/v4/{endpoint}",
                              headers=headers, json=data or {}, verify=False)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            self.console.print(f"[red]POST /{endpoint} failed: {e}[/red]")
            return r.json()

    def list_machines(self):
        d = self._get("machine/paginated?per_page=100") or {}
        tbl = Table("ID","Name","OS","Release","Difficulty","UserOwn","RootOwn", show_lines=True)
        for m in d.get("data", []):
            tbl.add_row(
                str(m["id"]), m["name"], m["os"],
                m["release"].split("T")[0], m["difficultyText"],
                str(m["authUserInUserOwns"]), str(m["authUserInRootOwns"])
            )
        self.console.print(tbl)
    
    def show_machine_detail(self, mid):
        d = self._get(f"machine/profile/{mid}") or {}
        info = d.get("info")
        if not info:
            self.console.print(f"[red]Machine ID {mid} not found[/red]")
            return

        tbl = Table(title=f"Machine Detail: {info.get('name')}", show_lines=True)
        tbl.add_column("Field", style="bold green")
        tbl.add_column("Value", style="cyan")

        tbl.add_row("ID", str(info.get("id")))
        tbl.add_row("Name", info.get("name", "-"))
        tbl.add_row("OS", info.get("os", "-"))
        tbl.add_row("Active", str(info.get("active")))
        tbl.add_row("Retired", str(info.get("retired")))
        tbl.add_row("Release Date", info.get("release", "-").split("T")[0])
        tbl.add_row("User Owned", str(info.get("authUserInUserOwns")))
        tbl.add_row("Root Owned", str(info.get("authUserInRootOwns")))
        tbl.add_row("User Own Time", info.get("authUserFirstUserTime", "-"))
        tbl.add_row("Root Own Time", info.get("authUserFirstRootTime", "-"))
        tbl.add_row("Own Rank", str(info.get("ownRank")))
        tbl.add_row("IP", str(info.get("ip")))

        self.console.print(tbl)

        # Print description below
        desc = (info.get("info_status") or "").strip()
        if desc:
            self.console.print(f"\n[bold green]Desc:[/bold green] {desc}")

    def list_sherlocks(self):
        d = self._get("sherlocks?state=active&per_page=100") or {}
        arr = sorted(
            d.get("data", []),
            key=lambda x: datetime.strptime(x["release_date"], "%Y-%m-%dT%H:%M:%S.%fZ"),
            reverse=True
        )
        tbl = Table("ID","Name","Diff","State","CatID","CatName","Owned","Released", show_lines=True)
        for x in arr:
            tbl.add_row(
                str(x["id"]), x["name"], x["difficulty"],
                x["state"], str(x["category_id"]),
                x["category_name"], str(x["is_owned"]),
                x["release_date"].split("T")[0]
            )
        self.console.print(tbl)

    def list_sherlock_tasks(self, s_id):
        d = self._get(f"sherlocks/{s_id}/tasks") or {}
        tasks = d.get("data", [])
        if not tasks:
            self.console.print(f"[yellow]No tasks found for Sherlock ID {s_id}[/yellow]")
            return

        for t in tasks:
            self.console.print(f"[bold cyan]Task ID:[/bold cyan] {t.get('id')}")
            self.console.print(f"[bold]Title:[/bold] {t.get('title', '-')}")
            self.console.print(f"[bold]Description:[/bold] {t.get('description', '-').strip()}")
            self.console.print(f"[bold]Flag:[/bold] {t.get('flag', '-')}")
            self.console.print(f"[bold]Masked Flag:[/bold] {t.get('masked_flag', '-')}")
            self.console.print(f"[bold]Hint:[/bold] {(t.get('hint') or '-' ).strip()}")
            self.console.print(f"[bold]Completed:[/bold] {'True' if t.get('completed') else 'False'}")
            self.console.print("-" * 50)


    def show_sherlock_detail(self, s_id):
        d = self._get(f"sherlocks/{s_id}/play") or {}
        info = d.get("data", {})
        if not info:
            self.console.print(f"[red]No details found for Sherlock ID {s_id}[/red]")
            return

        # Get progress
        progress = self._get(f"sherlocks/{s_id}/progress") or {}
        prog_data = progress.get("data", {})
        pct = prog_data.get("progress", 0)
        owned = prog_data.get("is_owned", False)
        total = prog_data.get("total_tasks", 0)
        done = prog_data.get("tasks_answered", 0)

        # Get download link
        dl = self._get(f"sherlocks/{s_id}/download_link") or {}
        dl_url = dl.get("url", "-")

        creators = ", ".join(c.get("name", "") for c in info.get("creators", []))

        self.console.print(f"[bold]Scenario:[/bold] {info.get('scenario', '-').strip()}")
        self.console.print()
        self.console.print(f"[bold]Created by:[/bold] {creators}")
        self.console.print(f"[bold]File:[/bold] {info.get('file_name', '-')}, Size: {info.get('file_size', '-')}")
        self.console.print(f"[bold]Download:[/bold]\n{dl_url}")
        self.console.print()
        self.console.print(f"[bold]Progress:[/bold] {pct}% ({done}/{total} tasks), Owned: {'True' if owned else 'False'}")
        self.console.print("-" * 60)

    def submit_sherlock_flag(self, s_id, t_id, flag):
        r = self._post(f"sherlocks/{s_id}/tasks/{t_id}/flag", {"flag": flag})
        if r:
            msg = r.get("message", "")
            if msg.lower() == "task flag owned!":
                self.console.print(f"[green] Correct flag submitted for Sherlock {s_id}, Task {t_id}[/green]")
            elif "already completed" in msg.lower():
                self.console.print(f"[yellow] Task {t_id} already completed[/yellow]")
            elif "incorrect" in msg.lower():
                self.console.print(f"[red] Incorrect flag for Task {t_id}[/red]")
            else:
                self.console.print(f"[blue] Response: {msg}[/blue]")
        else:
            self.console.print(f"[red]Failed to submit flag for Sherlock {s_id}, Task {t_id}[/red]")

    def print_release_machine(self, m):
        tbl = Table(title=f"Release Machine: {m.get('name')}", show_lines=True)
        tbl.add_column("Field", style="bold green")
        tbl.add_column("Value", style="cyan")

        tbl.add_row("ID", str(m.get("id")))
        tbl.add_row("Name", m.get("name", "-"))
        tbl.add_row("IP", str(m.get("ip", "-")))
        tbl.add_row("OS", m.get("os", "-"))
        tbl.add_row("Difficulty", m.get("difficulty_text", "-"))
        tbl.add_row("User Owned", str(m.get("is_owned_user", False)))
        tbl.add_row("Root Owned", str(m.get("is_owned_root", False)))
        tbl.add_row("Spawned", str(m.get("play_info", {}).get("is_spawned", False))) 

        self.console.print(tbl)

        desc = (m.get("info_status") or "").strip()
        if desc:
            self.console.print(f"\n[bold green]Desc:[/bold green] {desc}")


    def spawn_machine(self, mid):
        r =  self._post("vm/spawn", {"machine_id": mid})
        if r:
            print(r)
            self.console.print(f"[green]Spawned {mid}[/green]")

    def reset_machine(self, mid):
        self._post("vm/reset", {"machine_id": mid})
        self.console.print(f"[yellow]Reset {mid}[/yellow]")

    def terminate_machine(self, mid):
        self._post("vm/terminate", {"machine_id": mid})
        self.console.print(f"[red]Terminated {mid}[/red]")
        
    def submit_flag(self, mid, flag):
        """Submit a flag for a machine using API v5."""
        url = "https://labs.hackthebox.com/api/v5/machine/own"
        data = {"id": mid, "flag": flag}

        try:
            r = requests.post(url, headers=headers, json=data, verify=False, proxies=proxy)
            r.raise_for_status()
            resp = r.json()
            msg = resp.get("message", "")
            if resp.get("success"):
                self.console.print(f"[green] Flag submitted successfully for machine {mid}[/green]")
            else:
                self.console.print(f"[red] Failed to submit flag for machine {mid}: {msg}[/red]")
        except Exception as e:
            self.console.print(f"[red]POST /machine/own failed: {e}[/red]")

    def submit_flag_release(self, mid, flag):
        self._post("arena/own", {"id": mid, "flag": flag})
        self.console.print(f"[green]Flag submitted for {mid}[/green]")

def main():
    p = argparse.ArgumentParser("HTB CLI")
    sp = p.add_subparsers(dest="cmd")

    pm = sp.add_parser("machines", aliases=["m"], help="List or show machine detail")
    pm.add_argument("id", nargs="?", type=int, help="Machine ID to show detail")

    pr = sp.add_parser("release", aliases=["r"], help="Release Arena commands")
    sr = pr.add_subparsers(dest="rcmd")
    sr.add_parser("spawn", aliases=["s"], help="Spawn release")
    sr.add_parser("terminate", aliases=["t"], help="Terminate release")
    sr.add_parser("reset", aliases=["re"], help="Reset release")
    pf = sr.add_parser("flag", aliases=["f"], help="Submit release flag")
    pf.add_argument("flag")

    ps = sp.add_parser("spawn", aliases=["sp"], help="Spawn by ID")
    ps.add_argument("id", type=int)
    prt = sp.add_parser("reset", aliases=["re"], help="Reset by ID")
    prt.add_argument("id", type=int)
    pt = sp.add_parser("terminate", aliases=["t"], help="Terminate by ID")
    pt.add_argument("id", type=int)
    pf2 = sp.add_parser("flag", aliases=["f"], help="Submit flag by ID")
    pf2.add_argument("id", type=int)
    pf2.add_argument("flag")

    psh = sp.add_parser("sherlocks", aliases=["s"], help="Sherlock commands")
    psh.add_argument("action", nargs="?", help="f=sherlock_id task_id flag")
    psh.add_argument("id", nargs="?", help="Sherlock ID")
    psh.add_argument("task_id", nargs="?", help="Task ID (for flag submission)")
    psh.add_argument("flag", nargs="?", help="Flag to submit")

    args = p.parse_args()
    h = HTBClient()

    match args.cmd:
        case "machines"|"m":
            if hasattr(args, "id") and args.id:
                h.show_machine_detail(args.id)
            else:
                h.list_machines()

        case "sherlocks" | "s":
            if args.action == "f":
                if not (args.id and args.task_id and args.flag):
                    psh.print_help()
                    return
                h.submit_sherlock_flag(args.id, args.task_id, args.flag)

            elif args.action and args.action.isdigit():
                h.show_sherlock_detail(args.action)
                h.list_sherlock_tasks(args.action)

            else:
                h.list_sherlocks()

        case "release"|"r":
            res = h._get("season/machine/active") or {}
            m = res.get("data")
            if not m:
                h.console.print("[yellow]No active release machine[/yellow]")
                return
            match args.rcmd:
                case None:
                    h.print_release_machine(m)
                case "spawn"|"s":
                    h.spawn_machine(m["id"])
                    time.sleep(0.1)
                    res = h._get("season/machine/active") or {}
                    mm = res.get("data")
                    h.print_release_machine(mm)
                case "terminate"|"t":
                    h.terminate_machine(m["id"])
                case "reset"|"re":
                    h.reset_machine(m["id"])
                case "flag"|"f":
                    h.submit_flag_release(m["id"], args.flag)

        case "spawn"|"sp":
            h.spawn_machine(args.id)
            h.show_machine_detail(args.id)
        case "reset"|"re":
            h.reset_machine(args.id)
        case "terminate"|"t":
            h.terminate_machine(args.id)
        case "flag"|"f":
            h.submit_flag(args.id, args.flag)
        case _:
            p.print_help()
            
if __name__ == "__main__":
    main()

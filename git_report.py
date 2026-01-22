import subprocess
import argparse
import datetime
import os
import json
import time
from collections import defaultdict
from openpyxl import Workbook

# =========================
# LLM BACKENDS
# =========================

def gemini_summary(diff, commit_msg):
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("models/gemini-flash-latest")

    prompt = f"""
    Commit Message: "{commit_msg}"
    Summarize the FUNCTIONAL change in 3–8 words.
    Ignore formatting/imports.
    Diff:
    {diff}
    """

    return model.generate_content(prompt).text.strip()


def openai_summary(diff, commit_msg):
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"""
    Commit Message: "{commit_msg}"
    Summarize the FUNCTIONAL change in 3–8 words.
    Diff:
    {diff}
    """

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


def local_stub_summary(diff, commit_msg):
    # Placeholder for llama.cpp / ollama
    return commit_msg


LLM_PROVIDERS = {
    "gemini": gemini_summary,
    "openai": openai_summary,
    "local": local_stub_summary,
}

# =========================
# GIT HELPERS
# =========================

def git_log(author):
    cmd = ["git", "log", f"--author={author}", "--date=short", "--pretty=%ad|%s|%h"]
    return subprocess.check_output(cmd, text=True).splitlines()


def git_diff(commit):
    cmd = ["git", "show", commit, "--pretty=format:", "--unified=0"]
    return subprocess.check_output(cmd, text=True)[:20000]


# =========================
# REPORT LOGIC
# =========================

def parse_month(month_arg):
    if month_arg == "auto":
        now = datetime.datetime.now()
        return now.strftime("%Y-%m")
    return month_arg


def generate_report(author, month, llm):
    cache_file = "commit_cache.json"
    cache = json.load(open(cache_file)) if os.path.exists(cache_file) else {}

    daily = defaultdict(list)
    seen = defaultdict(set)

    for line in git_log(author):
        date, msg, hsh = line.split("|")
        if not date.startswith(month):
            continue
        if msg.startswith("Merge"):
            continue

        if hsh not in cache:
            diff = git_diff(hsh)
            cache[hsh] = LLM_PROVIDERS[llm](diff, msg)
            time.sleep(1)

        summary = cache[hsh]
        if summary not in seen[date]:
            daily[date].append(summary)
            seen[date].add(summary)

    json.dump(cache, open(cache_file, "w"), indent=2)
    return daily


def write_excel(data, month):
    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Activity", "Status"])

    for date in sorted(data.keys(), reverse=True):
        ws.append([
            date,
            ", ".join(data[date]),
            "Completed"
        ])

    os.makedirs("daily_reports", exist_ok=True)
    dt = datetime.datetime.strptime(month, "%Y-%m")
    fname = f"daily_reports/Work_Report_{dt.strftime('%B_%Y')}.xlsx"
    wb.save(fname)
    print(f"Generated: {fname}")


# =========================
# CLI
# =========================

def main():
    parser = argparse.ArgumentParser(description="AI Git Work Report Generator")
    parser.add_argument("--author", default="siraj", help="Git author name/email")
    parser.add_argument("--month", default="auto", help="YYYY-MM or auto")
    parser.add_argument("--llm", choices=LLM_PROVIDERS.keys(), default="gemini")

    args = parser.parse_args()
    month = parse_month(args.month)

    print(f"Generating report for {month} using {args.llm.upper()}...")
    data = generate_report(args.author, month, args.llm)
    write_excel(data, month)


if __name__ == "__main__":
    main()

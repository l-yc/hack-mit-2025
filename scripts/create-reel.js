#!/usr/bin/env node
/**
 * Node.js translation of scripts/create-reel.ps1
 * Requires Node 18+ (for global fetch)
 */

const fs = require('node:fs');
const fsp = require('node:fs/promises');
const path = require('node:path');
const { spawn } = require('node:child_process');

function printUsage() {
  console.log(`Usage: node scripts/create-reel.js --directory <path> --musicPath <path> [options]\n\n` +
    `Options:\n` +
    `  --directory <path>         Directory containing at least 2 .mp4 files (required)\n` +
    `  --musicPath <path>         Path/URL to music asset (required)\n` +
    `  --maxFiles <n>             Max number of video files to include (default: 20)\n` +
    `  --targetDurationSec <n>    Target duration in seconds (default: 30)\n` +
    `  --minDurationSec <n>       Minimum duration in seconds (default: 28)\n` +
    `  --maxDurationSec <n>       Maximum duration in seconds (default: 36)\n` +
    `  --perSegmentSec <n>        Per segment length in seconds (default: 3.0)\n` +
    `  --server <url>             Backend server base URL (default: http://localhost:6741)\n` +
    `  --help                     Show this help\n`);
}

function parseArgs(argv) {
  const args = {
    directory: undefined,
    musicPath: undefined,
    maxFiles: 20,
    targetDurationSec: 30,
    minDurationSec: 28,
    maxDurationSec: 36,
    perSegmentSec: 3.0,
    server: 'http://localhost:6741',
    help: false,
  };

  for (let i = 2; i < argv.length; i++) {
    const key = argv[i];
    const next = argv[i + 1];
    switch (key) {
      case '--help':
      case '-h':
        args.help = true;
        break;
      case '--directory':
      case '-d':
        args.directory = next; i++; break;
      case '--musicPath':
      case '-m':
        args.musicPath = next; i++; break;
      case '--maxFiles':
        args.maxFiles = Number.parseInt(next, 10); i++; break;
      case '--targetDurationSec':
        args.targetDurationSec = Number.parseFloat(next); i++; break;
      case '--minDurationSec':
        args.minDurationSec = Number.parseFloat(next); i++; break;
      case '--maxDurationSec':
        args.maxDurationSec = Number.parseFloat(next); i++; break;
      case '--perSegmentSec':
        args.perSegmentSec = Number.parseFloat(next); i++; break;
      case '--server':
      case '-s':
        args.server = next; i++; break;
      default:
        console.warn(`Unknown argument: ${key}`);
        break;
    }
  }

  return args;
}

async function pathExists(p) {
  try {
    await fsp.access(p, fs.constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

async function requireDirectoryWithTwoMp4s(directory) {
  if (!(await pathExists(directory))) {
    throw new Error(`Directory not found: ${directory}`);
  }
  const entries = await fsp.readdir(directory, { withFileTypes: true });
  const mp4Count = entries.filter(e => e.isFile() && e.name.toLowerCase().endsWith('.mp4')).length;
  if (mp4Count < 2) {
    throw new Error(`Need at least 2 .mp4 files in ${directory} (found ${mp4Count})`);
  }
}

async function requireFile(musicPath) {
  if (!(await pathExists(musicPath))) {
    throw new Error(`Music file not found: ${musicPath}`);
  }
}

function nowHHMMSS() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function openInDefaultBrowser(url) {
  const platform = process.platform; // 'win32', 'darwin', 'linux'
  try {
    if (platform === 'win32') {
      spawn('cmd', ['/c', 'start', '', url], { stdio: 'ignore', detached: true });
      return;
    }
    if (platform === 'darwin') {
      spawn('open', [url], { stdio: 'ignore', detached: true });
      return;
    }
    spawn('xdg-open', [url], { stdio: 'ignore', detached: true });
  } catch {
    // ignore best-effort open failures
  }
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help) {
    printUsage();
    process.exit(0);
  }

  if (!args.directory || !args.musicPath) {
    console.error('Error: --directory and --musicPath are required.');
    printUsage();
    process.exit(1);
  }

  console.log('Directory:', args.directory);
  console.log('MusicPath:', args.musicPath);

  try {
    await requireDirectoryWithTwoMp4s(args.directory);
    await requireFile(args.musicPath);
  } catch (err) {
    console.error(String(err.message || err));
    process.exit(1);
  }

  const body = {
    directory: args.directory,
    mode: 'montage',
    target_duration_sec: args.targetDurationSec,
    min_duration_sec: args.minDurationSec,
    max_duration_sec: args.maxDurationSec,
    per_segment_sec: args.perSegmentSec,
    max_files: args.maxFiles,
    aspect: '9:16',
    music_url: args.musicPath,
    music_only: true,
    end_with_low: true,
  };

  const json = JSON.stringify(body);
  console.log(`Posting job to ${args.server} ...`);
  console.log(json);

  let createResp;
  try {
    createResp = await fetch(`${args.server}/api/reels/jobs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: json,
    });
  } catch (err) {
    console.error(`Create job failed: ${String(err.message || err)}`);
    process.exit(1);
  }

  if (!createResp.ok) {
    const text = await createResp.text().catch(() => '');
    console.error(`Create job failed: HTTP ${createResp.status} ${createResp.statusText}\n${text}`);
    process.exit(1);
  }

  let createJson;
  try {
    createJson = await createResp.json();
  } catch {
    console.error('Invalid response from server');
    process.exit(1);
  }

  const jobId = createJson && createJson.job_id;
  if (!jobId) {
    console.error('Invalid response from server (missing job_id)');
    process.exit(1);
  }
  console.log('Job ID:', jobId);

  let statusJson = null;
  for (let i = 0; i < 600; i++) {
    let pollResp;
    try {
      pollResp = await fetch(`${args.server}/api/reels/jobs/${jobId}`);
    } catch (err) {
      console.warn(`Poll error: ${String(err.message || err)}`);
      await sleep(1000);
      continue;
    }
    if (!pollResp.ok) {
      console.warn(`Poll error: HTTP ${pollResp.status} ${pollResp.statusText}`);
      await sleep(1000);
      continue;
    }
    try {
      statusJson = await pollResp.json();
    } catch {
      await sleep(1000);
      continue;
    }

    const status = statusJson && statusJson.status;
    console.log(`[${nowHHMMSS()}] ${status}`);
    if (status === 'completed' || status === 'failed') {
      break;
    }
    await sleep(1000);
  }

  if (statusJson && statusJson.status === 'completed') {
    const bestPath = statusJson?.artifacts?.best_reel_mp4;
    const url = `${args.server}${bestPath ?? ''}`;
    console.log('Completed:', url);
    openInDefaultBrowser(url);
    process.exit(0);
  }

  const endStatus = statusJson ? statusJson.status : '(unknown)';
  console.warn(`Job ended with status: ${endStatus}`);
  if (endStatus === 'failed') {
    const jobPath = path.join(path.resolve('.'), 'uploads', 'reels', jobId, 'job.json');
    if (await pathExists(jobPath)) {
      console.log(`--- uploads/reels/${jobId}/job.json ---`);
      try {
        const content = await fsp.readFile(jobPath, 'utf8');
        console.log(content);
      } catch {}
    }
  }
  process.exit(1);
}

main().catch((err) => {
  console.error(err?.stack || String(err));
  process.exit(1);
});



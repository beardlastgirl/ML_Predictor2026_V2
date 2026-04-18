#!/usr/bin/env node
// gsd-hook-version: 1.32.0
// GSD Session Summary Hook
// Generates a summary of the session at SessionEnd

const fs = require('fs');
const path = require('path');
const os = require('os');

// Read JSON from stdin
let input = '';
// Timeout guard: if stdin doesn't close within 3s, exit silently
const stdinTimeout = setTimeout(() => process.exit(0), 3000);
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  clearTimeout(stdinTimeout);
  try {
    const data = JSON.parse(input);
    const sessionId = data.session_id || '';
    const model = data.model?.display_name || 'Claude';
    const workspace = data.workspace?.current_dir || process.cwd();
    const duration = data.session_duration || 0;
    
    // Generate session summary
    const summary = {
      session_id: sessionId,
      model: model,
      workspace: workspace,
      duration: duration,
      timestamp: new Date().toISOString(),
      files_modified: data.files_modified || [],
      tools_used: data.tools_used || [],
      context_usage: data.context_window || {}
    };
    
    // Write summary to logs directory
    const homeDir = os.homedir();
    const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(homeDir, '.gemini');
    const logsDir = path.join(claudeDir, 'logs');
    
    if (!fs.existsSync(logsDir)) {
      fs.mkdirSync(logsDir, { recursive: true });
    }
    
    const summaryFile = path.join(logsDir, `session-${sessionId}.json`);
    fs.writeFileSync(summaryFile, JSON.stringify(summary, null, 2));
    
    // Also write a human-readable summary
    const readableSummary = `
Session Summary
===============
Session ID: ${sessionId}
Model: ${model}
Workspace: ${workspace}
Duration: ${Math.round(duration / 1000)}s
Files Modified: ${summary.files_modified.length}
Tools Used: ${summary.tools_used.length}
Context Used: ${summary.context_usage.used_percentage || 'N/A'}%
Timestamp: ${summary.timestamp}
`;
    
    const readableFile = path.join(logsDir, `session-${sessionId}.txt`);
    fs.writeFileSync(readableFile, readableSummary);
    
    // Clean up old session files (keep last 10)
    try {
      const files = fs.readdirSync(logsDir)
        .filter(f => f.startsWith('session-') && f.endsWith('.json'))
        .map(f => ({ name: f, mtime: fs.statSync(path.join(logsDir, f)).mtime }))
        .sort((a, b) => b.mtime - a.mtime);
      
      if (files.length > 10) {
        files.slice(10).forEach(file => {
          try {
            fs.unlinkSync(path.join(logsDir, file.name));
            const txtFile = file.name.replace('.json', '.txt');
            if (fs.existsSync(path.join(logsDir, txtFile))) {
              fs.unlinkSync(path.join(logsDir, txtFile));
            }
          } catch (e) {
            // Ignore cleanup errors
          }
        });
      }
    } catch (e) {
      // Ignore cleanup errors
    }
    
  } catch (e) {
    // Silent fail - don't break session on summary errors
  }
});

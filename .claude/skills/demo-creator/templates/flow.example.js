// demo-creator flow template = the bundled sample-app demo (11 steps, two accounts, fully offline).
// Copy next to your steps.json as flow.js and change SITE, the selectors, the ids and the accounts.
// Every api.step id must exist in steps.json. Context 1 = admin, context 2 = a regular user.
//
// Accounts: identifiers may live here; PASSWORDS NEVER DO. Read them from the environment, e.g.
//   const PW = process.env.DEMO_ADMIN_PASS;   // set in the shell before recording
// The sample app accepts any password, so the template reads an env var with a harmless fallback.
const path = require('path');
const SITE = process.env.DEMO_SITE || ('file:///' + path.resolve(__dirname, 'sample-app', 'index.html').replace(/\\/g, '/'));
const ADMIN = 'admin@example.com';
const USER = 'jamie.user@example.com';
const PW = process.env.DEMO_PASS || 'demo';

// Generic login helper: adapt the selectors to the real login form. After login navigate with clicks
// only when the app keeps its session in memory (a page.goto can log it out).
async function login(api, page, email) {
  await page.goto(SITE, { waitUntil: 'domcontentloaded' });
  await api.overlay(page);
  const em = page.getByRole('textbox', { name: 'Email' });
  await em.waitFor();
  await api.clickIt(page, em);
  await em.fill(email);
  const pw = page.getByRole('textbox', { name: 'Password' });
  await api.clickIt(page, pw);
  await pw.fill(PW);
  await api.clickIt(page, page.getByRole('button', { name: 'Log In', exact: true }));
  await page.getByRole('heading', { name: /^Welcome,/ }).waitFor({ timeout: 45000 });
  await api.sleep(api.FAST ? 200 : 1500);
  await api.overlay(page);
}

module.exports = async (api) => {
  const { step, clickIt, select, flash, expandSection, heading, sleep, FAST } = api;
  const p1 = await api.ctx(1);

  await api.card(p1, { title: 'Notification settings', subtitle: 'Region and channel selection for the whole team', foot: 'Sample App · demo on local test data' });
  await step(p1, 'INTRO', async () => { await sleep(FAST ? 300 : 1500); });

  // ---- Part 1: admin
  await step(p1, 'P1-01', async () => { await login(api, p1, ADMIN); });
  await step(p1, 'P1-02', async () => {
    await flash(p1, p1.getByText('Open orders', { exact: true }), 1500);
    await flash(p1, p1.getByText('Notifications enabled', { exact: true }), 1500);
  });
  await step(p1, 'P1-03', async () => {
    await clickIt(p1, p1.getByRole('link', { name: 'Notification settings' }));
    await heading(p1, /^Notification settings/).waitFor({ timeout: 30000 });
  });
  await step(p1, 'P1-04', async () => {
    await select(p1, /^Region/, 'West');
    await p1.getByRole('combobox', { name: /^Region/ }).filter({ hasText: 'West' }).waitFor({ timeout: 10000 });
  });
  await step(p1, 'P1-05', async () => {
    await clickIt(p1, p1.getByRole('checkbox', { name: 'Weekly digest' }));
    await p1.getByText('4 of 4 channels enabled.').waitFor({ timeout: 10000 });
    await flash(p1, p1.getByText('4 of 4 channels enabled.'), 1200);
  });
  await step(p1, 'P1-06', async () => {
    await expandSection(p1, /^Show advanced options/);
    await flash(p1, p1.getByRole('checkbox', { name: /^Quiet hours/ }), 1500);
  });
  await step(p1, 'P1-07', async () => {
    await clickIt(p1, p1.getByRole('button', { name: 'Save Changes' }));
    await p1.getByText('Notification settings saved for region West.').first().waitFor({ timeout: 10000 });
  });

  // ---- Part 2: a regular user (second context)
  const p2 = await api.ctx(2);
  await step(p2, 'P2-01', async () => { await login(api, p2, USER); });
  await step(p2, 'P2-02', async () => {
    await flash(p2, p2.getByText('Notifications enabled', { exact: true }), 2000);
  });
  await step(p2, 'OUTRO', async () => {
    await api.endCard(p2, { title: 'Notification settings', subtitle: 'The admin sets region and channels once · every user sees the result', foot: 'End of demo' });
    await sleep(FAST ? 300 : 1500);
  });
};

import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import type { Page } from '@playwright/test';

const footage = resolve('../work/review-synthetic.mp4');
test.beforeAll(() => {
  execFileSync('ffmpeg', [
    '-v',
    'error',
    '-y',
    '-f',
    'lavfi',
    '-i',
    'testsrc2=size=320x180:rate=24',
    '-t',
    '20',
    '-c:v',
    'libx264',
    '-pix_fmt',
    'yuv420p',
    footage,
  ]);
});

test('prompt_and_review_before_export', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByLabel('Orientação extra para a IA')).toBeVisible();
  await page.getByLabel('Orientação extra para a IA').fill('Paisagem natural, rio e vegetação');
  await page.locator('input[type=file]').setInputFiles(footage);
  await page.getByRole('radio', { name: '15 segundos' }).check();
  await page.getByRole('button', { name: 'Analisar momentos' }).click();
  await expect(page.getByRole('heading', { name: 'Revê os teus momentos' })).toBeVisible({
    timeout: 90000,
  });
  const selection = page.locator('[data-testid="selected-moment"]');
  const initial = await selection.count();
  expect(initial).toBeGreaterThan(1);
  const ids = await selection.evaluateAll((nodes) => nodes.map((n) => n.getAttribute('data-id')));
  await selection.first().getByRole('button', { name: 'Mover para baixo' }).click();
  await expect(selection.first()).toHaveAttribute('data-id', ids[1]!);
  await selection.first().getByRole('button', { name: 'Pré-visualizar' }).click();
  await expect(page.locator('video')).toBeVisible();
  await expect
    .poll(() => page.locator('video').evaluate((v: HTMLVideoElement) => v.readyState))
    .toBeGreaterThanOrEqual(1);
  await selection.first().getByRole('button', { name: 'Remover momento' }).click();
  await expect(selection).toHaveCount(initial - 1);
  await page.getByLabel('Orientação extra para a IA').fill('Uma imagem vermelha');
  await expect(selection).toHaveCount(initial - 1);
  const suggestionResponse = page.waitForResponse((r) => r.url().endsWith('/suggest'));
  await page.getByRole('button', { name: 'Aplicar prompt' }).click();
  const suggestion = await (await suggestionResponse).json();
  await expect(selection).toHaveCount(suggestion.effectiveSegments.length);
  await page.getByRole('button', { name: 'Exportar', exact: false }).click();
  await expect(page.getByRole('heading', { name: 'O teu vídeo está pronto' })).toBeVisible({
    timeout: 90000,
  });
  await page.getByRole('button', { name: 'Voltar à revisão' }).click();
  await expect(page.getByRole('heading', { name: 'Revê os teus momentos' })).toBeVisible();
  await page.screenshot({ path: resolve('../work/ui-review.png'), fullPage: true });
});

test('review_keyboard_mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.locator('input[type=file]').setInputFiles(footage);
  await page.getByRole('button', { name: 'Analisar momentos' }).click();
  await expect(page.getByRole('heading', { name: 'Revê os teus momentos' })).toBeVisible({
    timeout: 90000,
  });
  const first = page.locator('[data-testid="selected-moment"]').first();
  await first.getByRole('button', { name: 'Mover para baixo' }).focus();
  await page.keyboard.press('Enter');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Restaurar seleção automática' }).click();
  await expect(page.getByRole('button', { name: /Exportar/ })).toBeEnabled();
  await page.screenshot({ path: resolve('../work/ui-review-mobile.png'), fullPage: true });
});

async function mockedReview(page: Page, failFirst = false) {
  const pid = '11111111-1111-4111-8111-111111111111';
  const candidates = [
    { id: 'a', start: 0, end: 3 },
    { id: 'b', start: 3, end: 11 },
    { id: 'c', start: 11, end: 19 },
  ].map((c) => ({
    ...c,
    filename: 'source.mp4',
    score: 70,
    aiScore: 70,
    reasons: ['Boa nitidez'],
    thumbnailUrl: '/missing.jpg',
    previewUrl: '/missing.mp4',
  }));
  const data = {
    candidates,
    selectedIds: ['a', 'b', 'c'],
    suggestedIds: ['a', 'b', 'c'],
    duration: 15,
    enhanceColors: true,
    prompt: '',
    warnings: [],
    effectiveDuration: 15,
    effectiveSegments: candidates,
  };
  await page.route('**/api/projects', (r) => r.fulfill({ json: { projectId: pid } }));
  await page.route('**/api/projects/*/videos', (r) => r.fulfill({ json: { projectId: pid } }));
  await page.route('**/api/projects/*/analyze', (r) =>
    r.fulfill({ status: 202, json: { projectId: pid } }),
  );
  await page.route('**/api/projects/*/status', (r) =>
    r.fulfill({
      json: {
        projectId: pid,
        status: 'review',
        progress: 70,
        stage: 'Pronto',
        stageKey: 'review',
        error: null,
        duration: 0,
        selectedMoments: 0,
        videos: 1,
      },
    }),
  );
  let calls = 0;
  await page.route('**/api/projects/*/review', (r) => {
    if (failFirst && calls++ === 0) return r.abort('failed');
    return r.fulfill({ json: data });
  });
  await page.goto('/');
  await page.locator('input[type=file]').setInputFiles(footage);
  await page.getByRole('button', { name: 'Analisar momentos' }).click();
}

test('reordering_has_no_hidden_moments', async ({ page }) => {
  await mockedReview(page);
  const selected = page.locator('[data-testid="selected-moment"]');
  await expect(selected).toHaveCount(3);
  await selected.first().getByRole('button', { name: 'Mover para baixo' }).click();
  await expect(selected.first()).toHaveAttribute('data-id', 'b');
  await selected.nth(1).getByRole('button', { name: 'Mover para baixo' }).click();
  await expect(selected).toHaveCount(2);
  await expect(page.locator('[data-testid="available-moment"]')).toHaveCount(1);
  await selected.first().getByRole('button', { name: 'Remover momento' }).click();
  await expect(selected).toHaveCount(1);
});

test('review_load_failure_can_retry', async ({ page }) => {
  await mockedReview(page, true);
  await expect(page.getByRole('button', { name: 'Tentar abrir a revisão' })).toBeVisible();
  await page.getByRole('button', { name: 'Tentar abrir a revisão' }).click();
  await expect(page.getByRole('heading', { name: 'Revê os teus momentos' })).toBeVisible();
});

test('replacement_and_preview_failure_are_actionable', async ({ page }) => {
  await mockedReview(page);
  const selected = page.locator('[data-testid="selected-moment"]');
  await expect(selected).toHaveCount(3);
  await selected.first().getByRole('button', { name: 'Remover momento' }).click();
  await selected.first().getByRole('button', { name: 'Substituir', exact: true }).click();
  await page
    .locator('[data-testid="available-moment"]')
    .first()
    .getByRole('button', { name: 'Substituir por este' })
    .click();
  await expect(selected.first()).toHaveAttribute('data-id', 'a');
  await selected.first().getByRole('button', { name: 'Pré-visualizar' }).click();
  await expect(page.getByRole('alert')).toContainText('Não foi possível abrir a pré-visualização');
  await page.getByRole('button', { name: 'Fechar pré-visualização' }).click();
  await expect(page.getByRole('button', { name: /Exportar/ })).toBeEnabled();
});

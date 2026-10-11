import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { resolve } from 'node:path';

const footage = resolve('../work/ui-synthetic.mp4');
test.beforeAll(() => {
  mkdirSync(resolve('../work'), { recursive: true });
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

test('valida ficheiros, permite remover e impede iniciar sem vídeos', async ({ page }) => {
  await page.goto('/');
  const create = page.getByRole('button', { name: 'Analisar momentos' });
  await expect(create).toBeDisabled();
  await page
    .locator('input[type=file]')
    .setInputFiles({ name: 'errado.txt', mimeType: 'text/plain', buffer: Buffer.from('inválido') });
  await expect(page.getByRole('alert')).toContainText('não é suportado');
  await expect(create).toBeDisabled();
  await page.locator('input[type=file]').setInputFiles(footage);
  await expect(create).toBeEnabled();
  await page.getByRole('button', { name: 'Remover ui-synthetic.mp4' }).click();
  await expect(create).toBeDisabled();
});

test('drag and drop e layout móvel mantêm as opções acessíveis', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  const data = await page.evaluateHandle(() => {
    const transfer = new DataTransfer();
    transfer.items.add(new File(['conteúdo de teste'], 'drop.mov', { type: 'video/quicktime' }));
    return transfer;
  });
  await page.locator('.dropzone').dispatchEvent('drop', { dataTransfer: data });
  await expect(page.getByRole('button', { name: 'Remover drop.mov' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Analisar momentos' })).toBeEnabled();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
});

test('uma recusa explícita de processamento permite tentar novamente', async ({ page }) => {
  await page.route('**/api/projects/*/analyze', (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'FFmpeg indisponível. Consulta o README.' }),
    }),
  );
  await page.goto('/');
  await page.locator('input[type=file]').setInputFiles(footage);
  await page.getByRole('button', { name: 'Analisar momentos' }).click();
  await expect(page.getByRole('alert')).toContainText('FFmpeg indisponível');
  await expect(page.getByRole('button', { name: 'Analisar momentos' })).toBeEnabled();
});

test('retomar após um pedido perdido não fica a aguardar um job inexistente', async ({ page }) => {
  await page.route('**/api/projects/*/analyze', (route) => route.abort('failed'));
  await page.goto('/');
  await page.locator('input[type=file]').setInputFiles(footage);
  await page.getByRole('button', { name: 'Analisar momentos' }).click();
  await page.getByRole('button', { name: 'Retomar consulta de progresso' }).click();
  await expect(page.getByRole('button', { name: 'Analisar momentos' })).toBeEnabled();
  await expect(page.getByRole('alert')).toContainText('não chegou a começar');
});

test('o utilizador cria 15 segundos, vê o vídeo e descarrega o MP4', async ({ page }) => {
  await page.goto('/');
  await page.locator('input[type=file]').setInputFiles(footage);
  await page.getByRole('radio', { name: '15 segundos' }).check();
  await page.getByRole('checkbox').uncheck();
  await page.getByRole('button', { name: 'Analisar momentos' }).click();
  await expect(page.getByRole('progressbar').first()).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Revê os teus momentos' })).toBeVisible({
    timeout: 90000,
  });
  await page.getByRole('button', { name: /Exportar/ }).click();
  await expect(page.getByRole('heading', { name: 'O teu vídeo está pronto' })).toBeVisible({
    timeout: 90000,
  });
  await expect(page.locator('.metadata')).toContainText('15 segundos');
  await expect(page.locator('.metadata')).toContainText('momentos selecionados');
  await expect(page.getByText('Selecionado com IA local')).toBeVisible();
  const videoUrl = await page.locator('video').getAttribute('src');
  const statusResponse = await page.request.get(videoUrl!.replace('/result', '/status'));
  const status = await statusResponse.json();
  expect(status.selectionMethod).toBe('local-ai');
  expect(status.aiModel).toContain('LAION');
  await expect
    .poll(() => page.locator('video').evaluate((video: HTMLVideoElement) => video.readyState))
    .toBeGreaterThanOrEqual(1);
  await page.locator('video').evaluate((video: HTMLVideoElement) => video.play());
  await expect
    .poll(() => page.locator('video').evaluate((video: HTMLVideoElement) => video.currentTime))
    .toBeGreaterThan(0);
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Descarregar vídeo' }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('final.mp4');
  await download.saveAs(resolve('../work/ui-final.mp4'));
  await page.screenshot({ path: resolve('../work/ui-result.png'), fullPage: true });
  await page.getByRole('button', { name: 'Criar outro vídeo' }).click();
  await expect(page.getByRole('button', { name: 'Analisar momentos' })).toBeDisabled();
});

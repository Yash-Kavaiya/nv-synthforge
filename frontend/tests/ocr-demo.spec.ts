import { test, expect } from '@playwright/test';

test.describe('NV-SynthForge Track C OCR Demo', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ocr');
  });

  test('OCR page loads with a sample picker or the empty-state CTA', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('OCR Structure Benchmark');
    // The backend database may or may not already hold invoice jobs; either state is valid.
    await expect(page.locator('select#ocr-sample').or(page.getByText('No invoice samples yet'))).toBeVisible();
    await expect(page.locator('button:has-text("Generate invoice pack")')).toBeVisible();
  });

  test('Can generate invoice pack and run noisy demo OCR', async ({ page }) => {
    // Click generate
    await page.click('button:has-text("Generate invoice pack")');

    // Wait for sample to appear (up to 60s)
    await expect(page.locator('select#ocr-sample')).toBeVisible({ timeout: 60000 });

    // Select the sample
    await page.selectOption('select#ocr-sample', { index: 0 });

    // Wait for PDF/image links to appear
    await expect(page.locator('a:has-text("Open PDF")')).toBeVisible({ timeout: 10000 });

    // Run noisy demo OCR
    await page.click('button:has-text("Run noisy demo OCR")');

    // Wait for report to render
    await expect(page.locator('text=FIELD-LEVEL STRUCTURE SCORE')).toBeVisible({ timeout: 60000 });

    // Verify accuracy shows
    await expect(page.locator('text=accuracy').first()).toBeVisible();

    // Verify group grid shows
    await expect(page.locator('text=identity').first()).toBeVisible();
    await expect(page.locator('text=parties').first()).toBeVisible();
    await expect(page.locator('text=amounts').first()).toBeVisible();
    await expect(page.locator('text=line_items').first()).toBeVisible();

    // Verify comparison table has rows
    await expect(page.locator('table.ocr-compare-table tbody tr').first()).toBeVisible();
  });

  test('Backend API proxy works', async ({ page }) => {
    const response = await page.request.get('/backend-api/api/v1/health');
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.status).toBe('ok');
  });
});
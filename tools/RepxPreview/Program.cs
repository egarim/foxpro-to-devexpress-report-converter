using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using DevExpress.XtraReports.UI;
using DevExpress.Drawing;

namespace RepxPreview;

/// <summary>
/// REPX Preview Tool - Renders DevExpress REPX reports to PNG images
/// </summary>
class Program
{
    static int Main(string[] args)
    {
        // Initialize DevExpress drawing with Skia
        DevExpress.Drawing.Settings.DrawingEngine = DevExpress.Drawing.DrawingEngine.Skia;
        
        if (args.Length == 0)
        {
            Console.WriteLine("REPX Preview Tool");
            Console.WriteLine("==================");
            Console.WriteLine("Usage: RepxPreview <report.repx> [output.png] [--all-pages]");
            Console.WriteLine();
            Console.WriteLine("Arguments:");
            Console.WriteLine("  <report.repx>  Path to the DevExpress report file");
            Console.WriteLine("  [output.png]   Optional output path (default: same name as input)");
            Console.WriteLine("  --all-pages    Export all pages (creates output_1.png, output_2.png, etc.)");
            Console.WriteLine();
            Console.WriteLine("Examples:");
            Console.WriteLine("  RepxPreview MyReport.repx");
            Console.WriteLine("  RepxPreview MyReport.repx preview.png");
            Console.WriteLine("  RepxPreview MyReport.repx preview.png --all-pages");
            return 1;
        }

        string inputPath = args[0];
        string outputPath = args.Length > 1 && !args[1].StartsWith("--") 
            ? args[1] 
            : Path.ChangeExtension(inputPath, ".png");
        bool allPages = args.Any(a => a == "--all-pages");

        if (!File.Exists(inputPath))
        {
            Console.WriteLine($"❌ Error: File not found: {inputPath}");
            return 1;
        }

        try
        {
            Console.WriteLine($"📄 Loading report: {inputPath}");
            
            // Load the report
            XtraReport report = new XtraReport();
            report.LoadLayoutFromXml(inputPath);
            
            Console.WriteLine($"   Page size: {report.PageWidth} x {report.PageHeight}");
            Console.WriteLine($"   Margins: {report.Margins}");

            // Create print document to render
            Console.WriteLine("🔄 Rendering report...");
            report.CreateDocument();

            int pageCount = report.Pages.Count;
            Console.WriteLine($"   Generated {pageCount} page(s)");

            if (pageCount == 0)
            {
                Console.WriteLine("⚠️ Warning: Report generated 0 pages. Creating empty preview.");
                // Create a blank preview showing the report structure
                CreateStructurePreview(report, outputPath);
            }
            else if (allPages)
            {
                // Export all pages
                string basePath = Path.ChangeExtension(outputPath, null);
                string ext = Path.GetExtension(outputPath);
                if (string.IsNullOrEmpty(ext)) ext = ".png";

                for (int i = 0; i < pageCount; i++)
                {
                    string pagePath = $"{basePath}_{i + 1}{ext}";
                    ExportPage(report, i, pagePath);
                    Console.WriteLine($"✅ Saved page {i + 1}: {pagePath}");
                }
            }
            else
            {
                // Export first page only
                ExportPage(report, 0, outputPath);
                Console.WriteLine($"✅ Saved preview: {outputPath}");
            }

            return 0;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"❌ Error: {ex.Message}");
            if (ex.InnerException != null)
            {
                Console.WriteLine($"   Inner: {ex.InnerException.Message}");
            }
            return 1;
        }
    }

    static void ExportPage(XtraReport report, int pageIndex, string outputPath)
    {
        // Export to image using DevExpress export
        using var stream = new MemoryStream();
        
        var imageExportOptions = new DevExpress.XtraPrinting.ImageExportOptions
        {
            Format = System.Drawing.Imaging.ImageFormat.Png,
            Resolution = 150, // DPI
            PageRange = $"{pageIndex + 1}"
        };
        
        report.ExportToImage(stream, imageExportOptions);
        
        stream.Position = 0;
        File.WriteAllBytes(outputPath, stream.ToArray());
    }

    static void CreateStructurePreview(XtraReport report, string outputPath)
    {
        // Create a simple preview showing the report structure when no data
        int width = (int)(report.PageWidth * 96 / 100); // Convert to pixels at 96 DPI
        int height = (int)(report.PageHeight * 96 / 100);
        
        using var bitmap = new Bitmap(width, height);
        using var graphics = Graphics.FromImage(bitmap);
        
        graphics.Clear(Color.White);
        
        // Draw border
        using var pen = new Pen(Color.LightGray, 2);
        graphics.DrawRectangle(pen, 1, 1, width - 3, height - 3);
        
        // Draw report info
        using var font = new Font("Arial", 12);
        using var brush = new SolidBrush(Color.Gray);
        
        string info = $"Report: {report.Name}\n" +
                      $"Page Size: {report.PageWidth} x {report.PageHeight}\n" +
                      $"Bands: {report.Bands.Count}\n" +
                      $"(No data - structure preview)";
        
        graphics.DrawString(info, font, brush, 20, 20);
        
        // Draw band structure
        int y = 100;
        foreach (Band band in report.Bands)
        {
            graphics.DrawString($"• {band.GetType().Name}: {band.Name} (Height: {band.HeightF})", 
                font, brush, 20, y);
            y += 25;
        }
        
        bitmap.Save(outputPath, ImageFormat.Png);
    }
}

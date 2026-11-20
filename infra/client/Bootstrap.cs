// Windows per-user installer and visible Task Manager identity for CF Client.
// The payload includes CPython and Client dependencies; the target PC needs no Python install.
using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Text;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly: AssemblyTitle("CF Client")]
[assembly: AssemblyDescription("Agent CF desktop client")]
[assembly: AssemblyVersion("0.3.4.0")]

static class Bootstrap {
    static string Quote(string text) { return "\"" + text.Replace("\\\"", "\\\\\"").Replace("\"", "\\\"") + "\""; }
    static string Home { get { return Environment.GetEnvironmentVariable("AGENT_CF_CLIENT_HOME") ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AgentCF"); } }
    [STAThread]
    static int Main(string[] args) {
        Application.EnableVisualStyles();
        try {
#if INSTALLER
            ShowInstaller(); return 0;
#else
            string root = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            // Shared read handle: installation cannot replace this client while any launch runs.
            using (var lifecycle = new FileStream(Path.Combine(root, "client.lock"), FileMode.Open, FileAccess.Read, FileShare.Read)) {
                string python = Path.Combine(root, "runtime", "pythonw.exe");
                var start = new ProcessStartInfo(python);
                var command = new StringBuilder(Quote(Path.Combine(root, "app", "agent_cf_client", "desktop", "entry.py")));
                foreach (string arg in args) command.Append(" ").Append(Quote(arg));
                start.Arguments = command.ToString(); start.UseShellExecute = false; start.CreateNoWindow = true;
                start.WorkingDirectory = root;
                start.EnvironmentVariables["AGENT_CF_CLIENT_EXE"] = Assembly.GetExecutingAssembly().Location;
                start.EnvironmentVariables["AGENT_CF_CLIENT_HOME"] = Home;
                string originalHome = Environment.GetEnvironmentVariable("PYTHONHOME");
                string originalUserSite = Environment.GetEnvironmentVariable("PYTHONNOUSERSITE");
                if (originalHome != null) start.EnvironmentVariables["AGENT_CF_ORIGINAL_PYTHONHOME"] = originalHome;
                if (originalUserSite != null) start.EnvironmentVariables["AGENT_CF_ORIGINAL_PYTHONNOUSERSITE"] = originalUserSite;
                start.EnvironmentVariables["PYTHONHOME"] = Path.Combine(root, "runtime");
                start.EnvironmentVariables["PYTHONNOUSERSITE"] = "1";
                start.EnvironmentVariables["PYTHONUTF8"] = "1";
                using (var process = Process.Start(start)) { process.WaitForExit(); return process.ExitCode; }
            }
#endif
        } catch (Exception) {
            MessageBox.Show("Khong mo/cai duoc CF Client. Neu Client dang chay, thoat o khay he thong roi thu lai.", "CF Client", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
#if INSTALLER
    static void ShowInstaller() {
        var form = new Form { Text = "Cài đặt CF Client", Width = 640, Height = 290, StartPosition = FormStartPosition.CenterScreen, FormBorderStyle = FormBorderStyle.FixedDialog, MaximizeBox = false };
        var title = new Label { Text = "Cài đặt CF Client", Left = 24, Top = 20, Width = 570, Height = 42, Font = new System.Drawing.Font("Segoe UI", 19, System.Drawing.FontStyle.Bold) };
        var info = new Label { Text = "Cài cho tài khoản Windows hiện tại, không cần quyền quản trị.\nSau khi cài, quay lại Web và bấm Mở CF Client.", Left = 24, Top = 70, Width = 570, Height = 50 };
        var startup = new CheckBox { Text = "Khởi động cùng Windows", Left = 24, Top = 133, Width = 350, Checked = false };
        var error = new Label { Left = 24, Top = 165, Width = 570, Height = 30, ForeColor = System.Drawing.Color.Firebrick };
        var install = new Button { Text = "Cài và mở CF Client", Left = 24, Top = 203, Width = 220, Height = 32 };
        install.Click += delegate {
            install.Enabled = false;
            try {
                string target = Install(startup.Checked);
                Process.Start(new ProcessStartInfo(target, "--desktop") { UseShellExecute = false, CreateNoWindow = true });
                form.Close();
            } catch (Exception) { error.Text = "Không cài được. Thoát CF Client ở khay hệ thống rồi thử lại."; install.Enabled = true; }
        };
        form.Controls.AddRange(new Control[] { title, info, startup, error, install }); Application.Run(form);
    }
    static string Install(bool startup) {
        string root = Path.GetFullPath(Path.Combine(Home, "Client")); Directory.CreateDirectory(root);
        string lockPath = Path.Combine(root, "client.lock");
        using (var lifecycle = new FileStream(lockPath, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None)) {
            using (Stream payload = Assembly.GetExecutingAssembly().GetManifestResourceStream("AgentCF.Payload"))
            using (var archive = new ZipArchive(payload, ZipArchiveMode.Read)) {
                foreach (ZipArchiveEntry entry in archive.Entries) {
                    string target = Path.GetFullPath(Path.Combine(root, entry.FullName));
                    if (!target.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) throw new IOException("Invalid bundle path");
                    if (entry.FullName.EndsWith("/")) { Directory.CreateDirectory(target); continue; }
                    Directory.CreateDirectory(Path.GetDirectoryName(target));
                    using (Stream input = entry.Open()) using (Stream output = File.Create(target)) input.CopyTo(output);
                }
            }
        }
        string executable = Path.Combine(root, "CF Client.exe");
        using (var key = Registry.CurrentUser.CreateSubKey(@"Software\Classes\agentcf")) { key.SetValue("", "URL:Agent CF Client"); key.SetValue("URL Protocol", ""); }
        using (var key = Registry.CurrentUser.CreateSubKey(@"Software\Classes\agentcf\shell\open\command")) key.SetValue("", Quote(executable) + " --connect \"%1\"");
        using (var key = Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run")) {
            if (startup) key.SetValue("CF Client", Quote(executable) + " --background");
            // Leaving unchecked never silently changes an existing startup preference.
        }
        string shortcut = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs), "CF Client.lnk");
        Type shellType = Type.GetTypeFromProgID("WScript.Shell"); object shell = Activator.CreateInstance(shellType);
        object link = shellType.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, shell, new object[] { shortcut });
        link.GetType().InvokeMember("TargetPath", BindingFlags.SetProperty, null, link, new object[] { executable });
        link.GetType().InvokeMember("Save", BindingFlags.InvokeMethod, null, link, null);
        return executable;
    }
#endif
}

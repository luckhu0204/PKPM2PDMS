// stub_pkpmjwd.cs - 契约 §p.2 编译命令的探针桩（不是交付的 Add-in 源码）
using System;
using Aveva.ApplicationFramework;
using Aveva.ApplicationFramework.Presentation;

namespace PKPMJWD
{
    public class StubAddin : IAddin
    {
        public string Name { get { return "PKPMJWD-stub"; } }
        public string Description { get { return "compile probe only"; } }
        public void Start(ServiceManager services)
        {
            CommandManager cm = (CommandManager)services.GetService(typeof(CommandManager));
            if (cm != null) cm.Commands.Add(new StubCommand());
        }
        public void Stop() { }
    }

    public class StubCommand : Command
    {
        public StubCommand()
        {
            Key = "PKPMJWD.StubProbe";
            Description = "probe";
        }
        public override bool IsValid { get { return true; } }
        public override void Execute() { }
    }
}

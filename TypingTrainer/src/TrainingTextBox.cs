// SPDX-License-Identifier: Apache-2.0
using System.Windows.Automation.Peers;
using System.Windows.Controls;
namespace TypingTrainer;
// Expose readable text/accessibility navigation while preventing UI Automation Value.SetValue bulk filling.
public sealed class TrainingTextBox : TextBox
{
    protected override AutomationPeer OnCreateAutomationPeer()=>new TrainingPeer(this);
    sealed class TrainingPeer(TrainingTextBox owner):TextBoxAutomationPeer(owner)
    {
        public override object? GetPattern(PatternInterface pattern)=>pattern==PatternInterface.Value?null:base.GetPattern(pattern);
    }
}

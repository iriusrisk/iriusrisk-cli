package io.github.lukacupic.irius.client.commands.configure;

import io.github.lukacupic.irius.client.commands.ErrorUtil;
import picocli.CommandLine;

import java.util.Map;

@CommandLine.Command(name = "configure", description = "Manage configuration properties", subcommands = {
        TokenCommand.class
})
public class ConfigureCommand implements Runnable {

    /**
     * Command line Spec for handling missing subcommands.
     */
    @CommandLine.Spec private CommandLine.Model.CommandSpec spec;

    /**
     * Constructor.
     */
    public ConfigureCommand() {
    }

    @CommandLine.Command(name = "list", description = "List all products")
    void listCommand() {
        Map<String, String> credentials = CredentialsUtil.readCredentials();
        if (credentials == null) {
            ErrorUtil.customError(spec, "Error while reading credentials. Does the file exist?");
        }

        System.out.println("{");
        for (String key : credentials.keySet()) {
            String string = String.format("  %s: %s", key, credentials.get(key));
            System.out.println(string);
        }
        System.out.println("}");
    }

    @Override
    public void run() {
        ErrorUtil.subcommandError(spec);
    }
}
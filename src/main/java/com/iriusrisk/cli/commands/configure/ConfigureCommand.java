package com.iriusrisk.cli.commands.configure;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.iriusrisk.cli.commands.IriusMapper;
import com.iriusrisk.cli.commands.ErrorUtil;
import picocli.CommandLine;

@CommandLine.Command(name = "configure", description = "Manage configuration properties", subcommands = {
        TokenCommand.class
})
public class ConfigureCommand implements Runnable {

    private static final IriusMapper iriusMapper = IriusMapper.getInstance();

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
        Credentials credentials = CredentialUtils.readCredentials();
        if (credentials == null) {
            ErrorUtil.customError(spec, "Error while reading credentials. Does the file exist?");
        }

        try {
            System.out.println(iriusMapper.writeValueAsString(credentials));
        } catch (JsonProcessingException e) {
            ErrorUtil.customError(spec, "Error while printing the credentials.");
        }
    }

    @Override
    public void run() {
        ErrorUtil.subcommandError(spec);
    }
}
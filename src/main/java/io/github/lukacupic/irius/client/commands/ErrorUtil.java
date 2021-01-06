package io.github.lukacupic.irius.client.commands;

import io.github.lukacupic.irius.client.Irius;
import picocli.CommandLine;

public class ErrorUtil {

    /**
     * Throws an API error.
     *
     * @param spec the CommandSpec, used for writing to command line.
     */
    public static void apiError(CommandLine.Model.CommandSpec spec) {
        String message;
        if (Irius.getInstance().getApiToken() == null) {
            message = "No API token found. To configure your API token please use command:\n" +
                    "  irius configure token set <api token>\n" +
                    "If you do not have an api token please contact your administrator.\n";
        } else {
            message = "Error while caling API";
        }

        throw new CommandLine.ParameterException(spec.commandLine(), message);
    }

    /**
     * Throws a "missing subcommand" error.
     *
     * @param spec the CommandSpec, used for writing to command line.
     */
    public static void subcommandError(CommandLine.Model.CommandSpec spec) {
        throw new CommandLine.ParameterException(spec.commandLine(), "Missing required subcommand");
    }

    /**
     * Throws a custom error.
     *
     * @param spec    the CommandSpec, used for writing to command line.
     * @param message the message
     */
    public static void customError(CommandLine.Model.CommandSpec spec, String message) {
        throw new CommandLine.ParameterException(spec.commandLine(), message);
    }
}

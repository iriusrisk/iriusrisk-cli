package com.iriusrisk.cli.commands.product;

import com.iriusrisk.api.client.ProductsApi;
import com.iriusrisk.api.client.model.Product;
import com.iriusrisk.api.client.model.ProductShort;
import com.iriusrisk.cli.Irius;
import com.iriusrisk.cli.commands.ErrorUtil;
import com.iriusrisk.cli.commands.configure.CredentialUtils;
import com.iriusrisk.iac.CfImport;
import org.springframework.web.client.RestClientException;
import picocli.CommandLine;

import java.util.List;

@CommandLine.Command(name = "product", description = "Display product related information")
public class ProductCommand implements Runnable {

  /**
   * Command line Spec for handling missing subcommands.
   */
  @CommandLine.Spec
  private CommandLine.Model.CommandSpec spec;

  /**
   * The Products API.
   */
  private ProductsApi api;

  /**
   * The API token.
   */
  private String token;

  /**
   * Constructor.
   */
  public ProductCommand() {
    this.api = Irius.getApi();
    this.token = Irius.getApiToken();
  }

  @CommandLine.Command(name = "list", description = "List all products")
  void listCommand() {
    CredentialUtils.checkToken(spec);

    try {
      List<ProductShort> products = api.productsGet(token, null, null, null);
      products.forEach(System.out::println);
    } catch (RestClientException e) {
      ErrorUtil.apiError(spec, e.getMessage());
    }
  }

  @CommandLine.Command(name = "show", description = "Display product details")
  void showCommand(@CommandLine.Parameters(paramLabel = "<product unique ID>", description = "Product ID") String id) {
    CredentialUtils.checkToken(spec);

    try {
      Product product = api.productsRefGet(token, id);
      System.out.println(product);
    } catch (RestClientException e) {
      ErrorUtil.apiError(spec, e.getMessage());
    }
  }

  //product create -n product_name -i product_id -cf ./my-cf-template [-mf xxxxx]
  @CommandLine.Command(name = "show", description = "Display product details")
  void createCommand(@CommandLine.Parameters(paramLabel = "<product name>", description = "Product Name") String name,
          @CommandLine.Parameters(paramLabel = "<product unique ID>", description = "Product ID") String id,
          @CommandLine.Parameters(paramLabel = "<CF Template>", description = "Cloudformation Template") String template,
          @CommandLine.Parameters(paramLabel = "<Mapping File>", description = "Iriusrisk Mapping File") String mapping) {
    CredentialUtils.checkToken(spec);

    try {
      CfImport cfImport = new CfImport();
      cfImport.setMappingFileName(template);
      cfImport.setMappingFileName(mapping);
      
      Product product = api.productsRefGet(token, id);
      System.out.println(product);
    } catch (RestClientException e) {
      ErrorUtil.apiError(spec, e.getMessage());
    }
  }

  @Override
  public void run() {
    ErrorUtil.subcommandError(spec);
  }
}

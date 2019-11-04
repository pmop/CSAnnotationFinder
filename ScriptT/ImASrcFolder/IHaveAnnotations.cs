namespace imanamespace {
	[IamAnAttribute]
	internal class IHaveAnnotations {
		public static readonly string ImAStringProportyWOAnnotations = "yeah";
		
		[IamTheSecondAttribute(with="value")]
		public string IamAnnotated {get; set;}
		
		[IamTheThirdAnnotation(with="two",value="values")]
		public string AnAnnotatedMethod() {
			return IamAnnotated + " indeed";
		}
	}
}